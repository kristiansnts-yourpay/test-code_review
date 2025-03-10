from github import Github
from typing import Dict, List, Optional

class PRClient:
    def __init__(self, github_token: str, repo_name: str, pr_number: int):
        self.g = Github(github_token)
        self.repo = self.g.get_repo(repo_name)
        self.pr = self.repo.get_pull(pr_number)
        self.file_changes = self._get_file_changes()

    def _get_file_changes(self) -> Dict:
        """Get all file changes in the PR."""
        file_changes = {}
        for file in self.pr.get_files():
            file_changes[file.filename] = {
                'patch': file.patch,
                'additions': file.additions,
                'deletions': file.deletions,
                'changes': file.changes,
                'blob_url': file.blob_url,
                'raw_url': file.raw_url,
                'status': file.status
            }
        return file_changes

    def post_review(self, review_content: str, as_review: bool = False) -> None:
        """Post a review comment or formal review."""
        if as_review:
            self.pr.create_review(body=review_content, event="COMMENT")
        else:
            self.pr.create_issue_comment(review_content)

    def post_inline_comments(self, comments: List[Dict], as_review: bool = False) -> None:
        """Post inline comments on specific lines."""
        # Create a cache for existing comments to avoid duplicates
        existing_comments = self._get_existing_comments()
        
        if as_review:
            review_comments = []
            for comment in comments:
                # Skip if a similar comment already exists
                if self._is_duplicate_comment(existing_comments, comment):
                    print(f"Skipping duplicate comment for {comment['path']}:{comment['line']}")
                    continue
                
                position = self._get_position_in_diff(comment['path'], comment['line'])
                if position is not None:
                    review_comments.append({
                        'path': comment['path'],
                        'position': position,
                        'body': comment['body']
                    })
            
            if review_comments:
                self.pr.create_review(comments=review_comments, event="COMMENT")
        else:
            for comment in comments:
                # Skip if a similar comment already exists
                if self._is_duplicate_comment(existing_comments, comment):
                    print(f"Skipping duplicate comment for {comment['path']}:{comment['line']}")
                    continue
                
                position = self._get_position_in_diff(comment['path'], comment['line'])
                if position is not None:
                    try:
                        self.pr.create_review_comment(
                            body=comment['body'],
                            commit_id=self.pr.get_commits().reversed[0].sha,
                            path=comment['path'],
                            position=position
                        )
                    except Exception as e:
                        print(f"Failed to create review comment for {comment['path']}:{comment['line']}: {str(e)}")

    def _get_position_in_diff(self, file_path: str, line_number: int) -> Optional[int]:
        """Convert a file line number to a position in the diff."""
        if file_path not in self.file_changes:
            return None
            
        patch = self.file_changes[file_path]['patch']
        if not patch:
            return None

        position = 0
        current_line = 0
        
        for line in patch.split('\n'):
            position += 1
            if line.startswith('@@'):
                import re
                match = re.search(r'@@ -\d+,\d+ \+(\d+),\d+ @@', line)
                if match:
                    current_line = int(match.group(1)) - 1
            elif line.startswith('+'):
                current_line += 1
                if current_line == line_number:
                    return position
            elif not line.startswith('-'):
                current_line += 1
        
        return None 

    def _get_existing_comments(self) -> List[Dict]:
        """Get all existing review comments on the PR."""
        comments = []
        for comment in self.pr.get_review_comments():
            comments.append({
                'path': comment.path,
                'line': comment.line or 0,
                'body': comment.body,
                'id': comment.id
            })
        return comments

    def _is_duplicate_comment(self, existing_comments: List[Dict], new_comment: Dict) -> bool:
        """Check if a similar comment already exists."""
        for existing in existing_comments:
            if (existing['path'] == new_comment['path'] and 
                existing['line'] == new_comment['line'] and
                new_comment['body'][:50] in existing['body']):
                return True
        return False 