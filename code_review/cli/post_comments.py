import argparse
import json
import os
import sys
from typing import Dict

from code_review.github_client.pr_client import PRClient
from code_review.parsers.review_parser import ReviewParser

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Post AI review comments to GitHub PR')
    parser.add_argument('review_file', help='JSON file containing the AI review')
    parser.add_argument('--create-review', action='store_true', help='Create a formal review instead of individual comments')
    parser.add_argument('--suggest-changes', action='store_true', help='Convert code suggestions to GitHub suggested changes')
    parser.add_argument('--inline-comments', action='store_true', help='Post comments inline on specific lines when possible')
    return parser.parse_args()

def load_review_data(review_file: str) -> Dict:
    """Load and validate review data from file."""
    with open(review_file, 'r') as f:
        review_data = json.load(f)
    
    if "error" in review_data:
        print(f"Error from API: {review_data['error']['message']}")
        sys.exit(1)
    
    if "choices" not in review_data or not review_data["choices"]:
        print("No review content found in the response")
        sys.exit(1)
    
    return review_data

def get_env_vars() -> tuple:
    """Get and validate required environment variables."""
    github_token = os.environ.get("GITHUB_TOKEN")
    pr_number = os.environ.get("PR_NUMBER")
    repo_name = os.environ.get("REPO_NAME")
    
    if not all([github_token, pr_number, repo_name]):
        print("Missing required environment variables")
        sys.exit(1)
    
    return github_token, int(pr_number), repo_name

def main():
    args = parse_args()
    review_data = load_review_data(args.review_file)
    github_token, pr_number, repo_name = get_env_vars()
    
    # Initialize GitHub client
    pr_client = PRClient(github_token, repo_name, pr_number)
    
    # Get review content
    review_content = review_data["choices"][0]["message"]["content"]
    
    # Process review content
    if args.suggest_changes:
        review_content = ReviewParser.process_code_suggestions(review_content, pr_client.file_changes)
    
    # Post comments
    if args.inline_comments:
        comments = ReviewParser.extract_inline_comments(review_content, pr_client.file_changes)
        if comments:
            pr_client.post_inline_comments(comments, args.create_review)
            print(f"Posted {len(comments)} inline comments to PR #{pr_number}")
        else:
            pr_client.post_review(review_content, args.create_review)
            print(f"Posted {'formal review' if args.create_review else 'review comment'} to PR #{pr_number}")
    else:
        pr_client.post_review(review_content, args.create_review)
        print(f"Posted {'formal review' if args.create_review else 'review comment'} to PR #{pr_number}")

if __name__ == "__main__":
    main() 