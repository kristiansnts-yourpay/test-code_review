import json
import os
import sys
import logging
from github import Github

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)
    
    if len(sys.argv) < 2:
        logger.error("Usage: python post_comments.py <review_file>")
        sys.exit(1)
    
    review_file = sys.argv[1]
    
    # Read the review JSON
    with open(review_file, 'r') as f:
        review_data = json.load(f)
    
    # Log the review data at debug level instead of always printing
    logger.debug("Review data: %s", json.dumps(review_data, indent=2))
    
    # Extract the review content - handle different possible response formats
    review_content = None
    
    # Try different possible paths in the JSON structure
    if 'choices' in review_data and len(review_data['choices']) > 0:
        if 'text' in review_data['choices'][0]:
            review_content = review_data['choices'][0]['text']
        elif 'message' in review_data['choices'][0]:
            review_content = review_data['choices'][0]['message'].get('content', '')
    
    # If still no content, try other common API response formats
    if not review_content and 'completion' in review_data:
        review_content = review_data['completion']
    
    if not review_content:
        logger.error("No review content found in the response")
        sys.exit(1)
    
    logger.info("Found review content: %s", 
                review_content[:100] + "..." if len(review_content) > 100 else review_content)
    
    # Get GitHub token and repository info from environment
    github_token = os.environ.get('GITHUB_TOKEN')
    if not github_token:
        logger.error("GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    repo_name = os.environ.get('GITHUB_REPOSITORY')
    pr_number_path = os.environ.get('GITHUB_EVENT_PATH')
    
    logger.info("Repository: %s", repo_name)
    logger.info("Event path: %s", pr_number_path)
    
    # If we have a GitHub event path, try to extract PR number from it
    pr_number = None
    if pr_number_path:
        with open(pr_number_path, 'r') as f:
            event_data = json.load(f)
            pr_number = event_data.get('pull_request', {}).get('number')
            logger.info("Extracted PR number: %s", pr_number)
    
    if not repo_name or not pr_number:
        logger.error("Could not determine repository or PR number")
        sys.exit(1)
    
    # Initialize GitHub client
    g = Github(github_token)
    repo = g.get_repo(repo_name)
    pr = repo.get_pull(int(pr_number))
    
    # Post the review as a comment
    pr.create_issue_comment(f"## AI Code Review\n\n{review_content}")
    logger.info("Successfully posted review comment")

if __name__ == "__main__":
    main() 