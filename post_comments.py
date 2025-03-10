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
            'changes': file.changes
        }
    
    if args.suggest_changes:
        # Process the review content to convert code blocks to suggested changes
        review_content = process_code_suggestions(review_content, file_changes)
    
    if args.create_review:
        # Create a formal review with the processed content
        pr.create_review(body=review_content, event="COMMENT")
        print(f"Posted formal review to PR #{pr_number}")
    else:
        # Post as a regular comment
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

if __name__ == "__main__":
    main() 