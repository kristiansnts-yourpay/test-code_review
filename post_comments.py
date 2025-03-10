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
    
    # Read the review data
    with open(review_file, 'r') as f:
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
    
    # Post the review as a comment
    pr.create_issue_comment(review_content)
    print(f"Posted review comment to PR #{pr_number}")

if __name__ == "__main__":
    main() 