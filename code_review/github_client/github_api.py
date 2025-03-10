"""GitHub API client for code review interactions."""
from typing import List, Dict, Optional
import requests
from dataclasses import dataclass

@dataclass
class ReviewComment:
    """Data class for review comments."""
    path: str
    line: int
    body: str
    position: Optional[int] = None

class GitHubAPI:
    """GitHub API client for code review interactions."""
    
    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        """Initialize GitHub API client.
        
        Args:
            token: GitHub API token
            base_url: Base URL for GitHub API
        """
        self.token = token
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        })

    def get_existing_comments(self, owner: str, repo: str, pr_number: int) -> List[Dict]:
        """Get existing review comments for a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            
        Returns:
            List of existing review comments
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        response = self.session.get(url)
        response.raise_for_status()
        return response.json()

    def create_review_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_id: str,
        path: str,
        line: int,
        body: str
    ) -> Dict:
        """Create a review comment on a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            commit_id: Commit SHA
            path: File path
            line: Line number
            body: Comment body
            
        Returns:
            Created comment data
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        data = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "side": "RIGHT"
        }
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json()

    def post_comment(self, owner: str, repo: str, pr_number: int, body: str) -> Dict:
        """Post a regular comment on a pull request.
        
        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment body
            
        Returns:
            Created comment data
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        data = {"body": body}
        response = self.session.post(url, json=data)
        response.raise_for_status()
        return response.json() 