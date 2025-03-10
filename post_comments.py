import json
import os
import sys
import argparse
import re
from github import Github

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Post AI review comments to GitHub PR')
    parser.add_argument('review_file', help='JSON file containing the AI review')
    parser.add_argument('--create-review', action='store_true', help='Create a formal review instead of individual comments')
    parser.add_argument('--suggest-changes', action='store_true', help='Convert code suggestions to GitHub suggested changes')
    parser.add_argument('--inline-comments', action='store_true', help='Post comments inline on specific lines when possible')
    args = parser.parse_args()
    
    # Read the review data
    with open(args.review_file, 'r') as f:
        review_data = json.load(f)
    
    print(f"Review data: {json.dumps(review_data, indent=2)}")
    
    # Check if there's an error in the response
    if "error" in review_data:
        print(f"Error from API: {review_data['error']['message']}")
        sys.exit(1)
    
    # Extract the review content from the API response
    if "choices" in review_data and len(review_data["choices"]) > 0:
        review_content = review_data["choices"][0]["message"]["content"]
    else:
        print("No review content found in the response")
        sys.exit(1)
    
    # Get environment variables
    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number = int(os.environ.get("PR_NUMBER"))
    repo_name = os.environ.get("REPO_NAME")
    
    if not all([github_token, pr_number, repo_name]):
        print("Missing required environment variables")
        sys.exit(1)
    
    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(pr_number)
    
    # Get the PR diff to help with file paths and line numbers
    diff_files = pr.get_files()
    file_changes = {}
    for file in diff_files:
        file_changes[file.filename] = {
            'patch': file.patch,
            'additions': file.additions,
            'deletions': file.deletions,
            'changes': file.changes,
            'blob_url': file.blob_url,
            'raw_url': file.raw_url,
            'status': file.status
        }
    
    if args.suggest_changes:
        # Process the review content to convert code blocks to suggested changes
        review_content = process_code_suggestions(review_content, file_changes)
    
    if args.inline_comments:
        # Extract inline comments and post them directly on the PR
        comments = extract_inline_comments(review_content, file_changes)
        if comments:
            post_inline_comments(pr, comments, args.create_review)
            print(f"Posted {len(comments)} inline comments to PR #{pr_number}")
        else:
            # If no inline comments were found, post the full review as a regular comment
            if args.create_review:
                pr.create_review(body=review_content, event="COMMENT")
                print(f"Posted formal review to PR #{pr_number}")
            else:
                pr.create_issue_comment(review_content)
                print(f"Posted review comment to PR #{pr_number}")
    else:
        # Post as a regular comment or review
        if args.create_review:
            pr.create_review(body=review_content, event="COMMENT")
            print(f"Posted formal review to PR #{pr_number}")
        else:
            pr.create_issue_comment(review_content)
            print(f"Posted review comment to PR #{pr_number}")

def process_code_suggestions(content, file_changes=None):
    """
    Process the review content to convert code blocks to GitHub suggested changes format.
    
    GitHub suggested changes format:
    ```suggestion
    new code here
    ```
    """
    # Pattern to find code blocks with language specifier and optional file path
    # This regex looks for markdown code blocks that might contain suggested changes
    pattern = r'```([a-zA-Z0-9_+-]+)(?::([^\n]+))?\n(.*?)\n```'
    
    # Pattern to identify "Correct:" sections in code examples
    correct_pattern = r'#\s*Correct:\s*\n(.*?)(?=\n\n|$)'
    
    def replacement(match):
        language = match.group(1) or ""
        file_path = match.group(2) if match.group(2) else None
        code = match.group(3)
        
        # Check if this is likely a code suggestion
        suggestion_indicators = [
            "should be", "change to", "replace with", "instead of", 
            "suggestion", "recommended", "fix", "correct", "improve"
        ]
        
        # Look for suggestion indicators in the 3 lines before the code block
        context_start = max(0, content.find(match.group(0)) - 300)
        context_end = content.find(match.group(0))
        context = content[context_start:context_end].lower()
        
        is_suggestion = any(indicator in context for indicator in suggestion_indicators)
        
        # Check if this is a "Correct:" section from a code example
        correct_match = re.search(correct_pattern, code, re.DOTALL)
        if correct_match:
            code = correct_match.group(1).strip()
            is_suggestion = True
        
        # If it has a file path or looks like a suggestion, convert to suggestion format
        if file_path or is_suggestion:
            # If we have a file path, add it as a comment before the suggestion
            prefix = f"In `{file_path}`:\n" if file_path else ""
            return f"{prefix}```suggestion\n{code}\n```"
        else:
            # Keep the original code block
            return f"```{language}\n{code}\n```"
    
    # Replace code blocks with suggestion format
    processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # Add a note about suggested changes at the top of the review
    if processed_content != content:
        processed_content = (
            "## AI Code Review\n\n"
            "> Note: This review includes suggested code changes that can be directly applied.\n\n"
            + processed_content
        )
    
    return processed_content

def extract_file_and_line_info(context):
    """
    Extract file path and line numbers from context around a code suggestion.
    Returns (file_path, start_line, end_line) or (None, None, None) if not found.
    """
    # Pattern to match file paths and line numbers like "file.py:10-20" or "path/to/file.py line 15"
    file_pattern = r'(?:in|file|at)\s+[`\'"]?([a-zA-Z0-9_\-./\\]+\.[a-zA-Z0-9]+)[`\'"]?(?:\s+(?:line[s]?|:)\s*(\d+)(?:\s*-\s*(\d+))?)?'
    
    match = re.search(file_pattern, context, re.IGNORECASE)
    if match:
        file_path = match.group(1)
        start_line = int(match.group(2)) if match.group(2) else None
        end_line = int(match.group(3)) if match.group(3) else start_line
        return file_path, start_line, end_line
    
    return None, None, None

def extract_inline_comments(content, file_changes):
    """
    Extract comments that should be posted inline on specific lines of code.
    Returns a list of dictionaries with file path, line number, and comment text.
    """
    comments = []
    
    # Look for file references in the content
    file_patterns = [
        # Match "In file.py:10:" or "In file.py (line 10):" patterns
        r'(?:In|At|File)\s+`?([^:`\s]+)`?(?:\s+\(line\s+(\d+)\)|:(\d+))(?:\s*-\s*(\d+))?',
        # Match "file.py:10:" pattern
        r'`?([^:`\s]+)`?:(\d+)(?:\s*-\s*(\d+))?:',
    ]
    
    # Split the content into sections that might be separate comments
    sections = re.split(r'\n\s*\n', content)
    
    for section in sections:
        for pattern in file_patterns:
            matches = re.finditer(pattern, section, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                # Different patterns capture line numbers in different groups
                line_num = None
                for i in range(2, 5):
                    if match.group(i) and not line_num:
                        line_num = int(match.group(i))
                
                if file_path and line_num and file_path in file_changes:
                    # Extract the comment text - everything after the file reference
                    comment_text = section[match.end():].strip()
                    if comment_text:
                        comments.append({
                            'path': file_path,
                            'line': line_num,
                            'body': comment_text
                        })
    
    # If no structured comments were found, try to extract from code blocks with file paths
    if not comments:
        code_block_pattern = r'```([a-zA-Z0-9_+-]+)(?::([^\n]+))?\n(.*?)\n```'
        matches = re.finditer(code_block_pattern, content, flags=re.DOTALL)
        for match in matches:
            file_path = match.group(2)
            if file_path and file_path in file_changes:
                # Look for context around this code block to use as a comment
                start_pos = max(0, content.rfind('\n\n', 0, match.start()))
                context = content[start_pos:match.start()].strip()
                if context:
                    # Try to find a line number in the context
                    line_match = re.search(r'line\s+(\d+)', context, re.IGNORECASE)
                    if line_match:
                        line_num = int(line_match.group(1))
                        comments.append({
                            'path': file_path,
                            'line': line_num,
                            'body': context
                        })
    
    return comments

def post_inline_comments(pr, comments, as_review=False):
    """
    Post comments directly on specific lines of code in the PR.
    
    Args:
        pr: The GitHub PR object
        comments: List of dictionaries with path, line, and body
        as_review: Whether to post as part of a review or as individual comments
    """
    if as_review:
        # Create a review with multiple comments
        review_comments = []
        for comment in comments:
            review_comments.append({
                'path': comment['path'],
                'position': get_position_in_diff(pr, comment['path'], comment['line']),
                'body': comment['body']
            })
        
        # Filter out comments where position couldn't be determined
        valid_comments = [c for c in review_comments if c['position'] is not None]
        
        if valid_comments:
            pr.create_review(comments=valid_comments, event="COMMENT")
    else:
        # Post individual comments
        for comment in comments:
            position = get_position_in_diff(pr, comment['path'], comment['line'])
            if position is not None:
                pr.create_review_comment(
                    body=comment['body'],
                    commit_id=pr.get_commits().reversed[0].sha,
                    path=comment['path'],
                    position=position
                )

def get_position_in_diff(pr, file_path, line_number):
    """
    Convert a file line number to a position in the diff.
    Returns None if the line is not part of the diff.
    """
    # Get the diff for this file
    diff_files = [f for f in pr.get_files() if f.filename == file_path]
    if not diff_files:
        return None
    
    file_diff = diff_files[0]
    patch = file_diff.patch
    
    if not patch:
        return None
    
    # Parse the patch to find the position
    position = 0
    current_line = 0
    
    for line in patch.split('\n'):
        position += 1
        if line.startswith('@@'):
            # Parse the @@ line to get the starting line number
            match = re.search(r'@@ -\d+,\d+ \+(\d+),\d+ @@', line)
            if match:
                current_line = int(match.group(1)) - 1
        elif line.startswith('+'):
            current_line += 1
            if current_line == line_number:
                return position
        elif not line.startswith('-'):
            # Context lines and other non-removal lines increment the line counter
            current_line += 1
    
    return None

if __name__ == "__main__":
    main() 