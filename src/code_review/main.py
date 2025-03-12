import os
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from unidiff import PatchSet
from minimatch import Minimatch

from .github import GitHubAPI
from .openrouter import OpenRouterAPI
from .config import REVIEW_CONFIG

# Cache for existing comments
existing_comments_cache = None

async def get_existing_comments(github: GitHubAPI, owner: str, repo: str, pr_number: str) -> List[Dict[str, Any]]:
    global existing_comments_cache
    if existing_comments_cache is None:
        existing_comments_cache = await github.get_existing_comments(owner, repo, pr_number)
    return existing_comments_cache

def find_existing_comment(existing_comments: List[Dict[str, Any]], new_comment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return next(
        (existing for existing in existing_comments
         if existing['path'] == new_comment['path']
         and existing['line'] == new_comment['line']
         and existing['body'].startswith(new_comment['message'][:50])),  # Compare first 50 chars
        None
    )

def merge_comments(comments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    merged_comments = {}

    for comment in comments:
        key = f"{comment['path']}:{comment['line']}"
        if key not in merged_comments:
            merged_comments[key] = {
                **comment,
                'body': f"{REVIEW_CONFIG['emojis'].get(comment['type'], '💭')} **{comment['type'].upper()}** ({comment['severity']})\n\n{comment['message']}"
            }
        else:
            existing = merged_comments[key]
            existing['body'] += f"\n\n{REVIEW_CONFIG['emojis'].get(comment['type'], '💭')} **{comment['type'].upper()}** ({comment['severity']})\n\n{comment['message']}"

    return list(merged_comments.values())

def get_changed_lines(chunk: Dict[str, Any]) -> Dict[str, Any]:
    changed_lines = {}
    added_line_numbers = set()
    position = chunk['new_start']

    # First pass: collect all lines with their proper numbers and mark added lines
    for change in chunk['changes']:
        if change['type'] in ['add', 'normal']:
            line_num = change.get('ln') or change.get('ln2')
            if line_num:
                changed_lines[line_num] = {
                    'content': change['content'],
                    'type': change['type'],
                    'position': line_num  # Use actual line number as position
                }
                if change['type'] == 'add':
                    added_line_numbers.add(line_num)

    # Include context lines
    context_lines = {}
    for line_num in added_line_numbers:
        # Include 3 lines before and after each changed line
        for i in range(max(1, line_num - 3), line_num + 4):
            if i in changed_lines:
                context_lines[i] = changed_lines[i]

    return {
        'context': context_lines,
        'added_lines': list(added_line_numbers)
    }

async def process_chunk(chunk: Dict[str, Any], file: Dict[str, Any], github: GitHubAPI, openrouter: OpenRouterAPI):
    changed_data = get_changed_lines(chunk)
    added_lines = changed_data['added_lines']
    if not added_lines:
        return

    # Create a string with line numbers, content, and markers for changed lines
    content_with_lines = '\n'.join(
        f"{line_num}:{' [CHANGED] ' if data['type'] == 'add' else ' '}{data['content'].strip()}"
        for line_num, data in sorted(changed_data['context'].items())
    )

    print(f"Reviewing {file['to']} with context:\n{content_with_lines}")
    print('Changed lines:', added_lines)

    reviews = await openrouter.review_code(content_with_lines, file['to'], added_lines)
    print('Received reviews:', reviews)

    comments_to_post = []
    for review in reviews:
        if not review['line'] or review['line'] not in added_lines:
            print(f"Skipping review for invalid line number: {review['line']}")
            continue

        line_data = changed_data['context'].get(review['line'])
        if not line_data:
            print(f"No context found for line {review['line']}")
            continue

        comments_to_post.append({
            **review,
            'path': file['to'],
            'line': review['line'],  # Use the actual line number
            'message': review['message']
        })

    merged_comments = merge_comments(comments_to_post)
    existing_comments = await get_existing_comments(
        github,
        os.getenv('GITHUB_REPOSITORY_OWNER'),
        os.getenv('GITHUB_REPOSITORY').split('/')[1],
        os.getenv('PR_NUMBER')
    )

    for comment in merged_comments:
        try:
            existing_comment = find_existing_comment(existing_comments, comment)
            if existing_comment:
                print(
                    f"Skipping duplicate comment for {comment['path']}:{comment['line']} as it already exists"
                )
                continue

            print(f"Creating comment for {comment['path']} at line {comment['line']}:")
            print(f"Content at line: {changed_data['context'][comment['line']]['content']}")

            await github.create_review_comment(
                os.getenv('GITHUB_REPOSITORY_OWNER'),
                os.getenv('GITHUB_REPOSITORY').split('/')[1],
                os.getenv('PR_NUMBER'),
                os.getenv('GITHUB_SHA'),
                comment['path'],
                comment['line'],
                comment['body']
            )
        except Exception as error:
            print(
                f"Failed to create review comment for {comment['path']}:{comment['line']}:",
                str(error)
            )

async def main():
    try:
        github = GitHubAPI(os.getenv('GITHUB_TOKEN'))
        openrouter = OpenRouterAPI()

        # Use the GitHub event's base branch or fall back to 'main'
        base_branch = os.getenv('BASE_BRANCH', 'origin/main')
        
        # Fetch the base branch to ensure it exists
        try:
            subprocess.run(['git', 'fetch', '--no-tags', '--prune', '--depth=1', 'origin', '+refs/heads/*:refs/remotes/origin/*'],
                         check=True, capture_output=True, text=True)
            print('Fetched remote branches')
        except subprocess.CalledProcessError as fetch_error:
            print('Warning: Failed to fetch branches:', fetch_error.stderr)
        
        # Get the diff between the base branch and current HEAD
        try:
            diff_output = subprocess.run(['git', 'diff', base_branch, 'HEAD'],
                                       check=True, capture_output=True, text=True).stdout
        except subprocess.CalledProcessError as diff_error:
            print(f"Failed to diff against {base_branch}, falling back to comparing with HEAD~1")
            diff_output = subprocess.run(['git', 'diff', 'HEAD~1', 'HEAD'],
                                       check=True, capture_output=True, text=True).stdout
        
        # Parse the diff using unidiff
        patch_set = PatchSet(diff_output)
        
        # Convert to a format similar to what parse-diff would provide
        files = []
        for patched_file in patch_set:
            chunks = []
            for hunk in patched_file:
                changes = []
                position = 0
                for line in hunk:
                    if line.is_added:
                        changes.append({
                            'type': 'add',
                            'content': line.value,
                            'ln': line.target_line_no
                        })
                    elif line.is_removed:
                        changes.append({
                            'type': 'del',
                            'content': line.value,
                            'ln': line.source_line_no
                        })
                    else:
                        changes.append({
                            'type': 'normal',
                            'content': line.value,
                            'ln': line.target_line_no or line.source_line_no
                        })
                    position += 1
                
                chunks.append({
                    'content': hunk.section_header,
                    'changes': changes,
                    'new_start': hunk.target_start,
                    'new_lines': hunk.target_length
                })
            
            files.append({
                'from': patched_file.source_file,
                'to': patched_file.target_file,
                'chunks': chunks
            })
        
        file_pattern = os.getenv('FILE_PATTERN')
        files_to_review = [
            file for file in files
            if file['to'] and Minimatch(file_pattern).match(file['to'])
        ]

        print(f"Found {len(files)} changed files")
        print(f"Reviewing {len(files_to_review)} files")

        chunks = [
            {'chunk': chunk, 'file': file}
            for file in files_to_review
            for chunk in file['chunks']
        ]

        for i in range(0, len(chunks), REVIEW_CONFIG['concurrency_limit']):
            batch = chunks[i:i + REVIEW_CONFIG['concurrency_limit']]
            await asyncio.gather(*(
                process_chunk(item['chunk'], item['file'], github, openrouter)
                for item in batch
            ))

        print('Code review completed successfully')
    except Exception as error:
        print('Error in code review process:', str(error))
        raise

if __name__ == '__main__':
    asyncio.run(main()) 