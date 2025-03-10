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
    
    if args.suggest_changes:
        # Process the review content to convert code blocks to suggested changes
        review_content = process_code_suggestions(review_content)
    
    if args.create_review:
        # Create a formal review with the processed content
        pr.create_review(body=review_content, event="COMMENT")
        print(f"Posted formal review to PR #{pr_number}")
    else:
        # Post as a regular comment
        pr.create_issue_comment(review_content)
        print(f"Posted review comment to PR #{pr_number}")

def process_code_suggestions(content):
    """
    Process the review content to convert code blocks to GitHub suggested changes format.
    
    GitHub suggested changes format:
    ```suggestion
    new code here
    ```
    """
    # Pattern to find code blocks with language specifier
    # This regex looks for markdown code blocks that might contain suggested changes
    pattern = r'```([a-zA-Z0-9_+-]+)?\n(.*?)\n```'
    
    def replacement(match):
        language = match.group(1) or ""
        code = match.group(2)
        
        # If it looks like a code suggestion (not just an example or output)
        # This is a simple heuristic - you might want to improve this logic
        if "should be" in content.lower() or "change to" in content.lower() or "replace with" in content.lower():
            return f"```suggestion\n{code}\n```"
        else:
            # Keep the original code block
            return f"```{language}\n{code}\n```"
    
    # Replace code blocks with suggestion format
    processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    return processed_content

if __name__ == "__main__":
    main() 