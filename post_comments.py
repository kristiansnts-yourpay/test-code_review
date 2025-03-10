import json
import os
import sys
import requests
from github import Github

def main():
    if len(sys.argv) < 2:
        print("Usage: python post_comments.py <review_file>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    
    # Read the review JSON
    with open(review_file, 'r') as f:
        review_data = json.load(f)
    
    # Extract the review content
    review_content = review_data.get('choices', [{}])[0].get('text', '')
    if not review_content:
        print("No review content found")
        sys.exit(1)
    
    # Get GitHub token and repository info from environment
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        print("GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    repo_name = os.environ.get('GITHUB_REPOSITORY')
    pr_number = os.environ.get('GITHUB_EVENT_PATH')
    
    # If we have a GitHub event path, try to extract PR number from it
    if pr_number:
        with open(pr_number, 'r') as f:
            event_data = json.load(f)
            pr_number = event_data.get('pull_request', {}).get('number')
    
    if not repo_name or not pr_number:
        print("Could not determine repository or PR number")
        sys.exit(1)
    
    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    # Post the review as a comment
    pr.create_issue_comment(f"## AI Code Review\n\n{review_content}")
    print("Successfully posted review comment")

if __name__ == "__main__":
    main() 