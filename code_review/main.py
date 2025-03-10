"""Main module for code review functionality."""
import os
import re
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import subprocess
from unidiff import PatchSet
from .github_client.github_api import GitHubAPI
from .stats import ReviewStats
from .config import REVIEW_CONFIG

@dataclass
class CodeChange:
    """Represents a code change in a file."""
    path: str
    content: str
    line_number: int
    change_type: str
    context: Dict[int, str]

class CodeReviewer:
    """Main class for handling code reviews."""

    def __init__(
        self,
        github_token: str,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        base_branch: str = "origin/main"
    ):
        """Initialize code reviewer.
        
        Args:
            github_token: GitHub API token
            repo_owner: Repository owner
            repo_name: Repository name
            pr_number: Pull request number
            base_branch: Base branch to compare against
        """
        self.github = GitHubAPI(github_token)
        self.stats = ReviewStats()
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.base_branch = base_branch
        self._existing_comments_cache = None

    async def get_existing_comments(self) -> List[Dict]:
        """Get existing review comments with caching.
        
        Returns:
            List of existing comments
        """
        if self._existing_comments_cache is None:
            self._existing_comments_cache = await self.github.get_existing_comments(
                self.repo_owner,
                self.repo_name,
                self.pr_number
            )
        return self._existing_comments_cache

    def _find_existing_comment(self, new_comment: Dict) -> Optional[Dict]:
        """Find if a similar comment already exists.
        
        Args:
            new_comment: New comment to check
            
        Returns:
            Existing similar comment if found, None otherwise
        """
        if not self._existing_comments_cache:
            return None

        return next(
            (
                existing for existing in self._existing_comments_cache
                if existing["path"] == new_comment["path"]
                and existing["line"] == new_comment["line"]
                and existing["body"].startswith(new_comment["body"][:50])
            ),
            None
        )

    def _merge_comments(self, comments: List[Dict]) -> List[Dict]:
        """Merge comments on the same line.
        
        Args:
            comments: List of comments to merge
            
        Returns:
            List of merged comments
        """
        merged = {}
        for comment in comments:
            key = f"{comment['path']}:{comment['line']}"
            emoji = REVIEW_CONFIG["emojis"].get(comment["type"], "💭")
            body = f"{emoji} **{comment['type'].upper()}** ({comment['severity']})\n\n{comment['message']}"
            
            if key not in merged:
                merged[key] = {**comment, "body": body}
            else:
                merged[key]["body"] += f"\n\n{body}"
        
        return list(merged.values())

    def _get_file_changes(self, patch_set: PatchSet) -> List[CodeChange]:
        """Extract file changes from a patch set.
        
        Args:
            patch_set: Unified diff patch set
            
        Returns:
            List of code changes
        """
        changes = []
        for patched_file in patch_set:
            if not re.search(REVIEW_CONFIG["supported_extensions"], patched_file.path):
                continue

            for hunk in patched_file:
                context = {}
                for line in hunk:
                    if line.is_added or line.is_context:
                        context[line.target_line_no] = line.value.rstrip()
                    
                    if line.is_added:
                        changes.append(CodeChange(
                            path=patched_file.path,
                            content=line.value.rstrip(),
                            line_number=line.target_line_no,
                            change_type="add",
                            context={
                                k: v for k, v in context.items()
                                if abs(k - line.target_line_no) <= 3
                            }
                        ))
        
        return changes

    async def review_changes(self) -> None:
        """Review code changes and post comments."""
        try:
            # Get diff from git
            diff_output = subprocess.check_output(
                ["git", "diff", self.base_branch, "HEAD"],
                text=True
            )
            patch_set = PatchSet(diff_output)
            
            # Get file changes
            changes = self._get_file_changes(patch_set)
            print(f"Found {len(changes)} code changes to review")

            # Process changes in batches
            for i in range(0, len(changes), REVIEW_CONFIG["concurrency_limit"]):
                batch = changes[i:i + REVIEW_CONFIG["concurrency_limit"]]
                await asyncio.gather(*(
                    self._process_change(change)
                    for change in batch
                ))

            # Generate and post summary
            summary = self.stats.generate_summary()
            await self.github.post_comment(
                self.repo_owner,
                self.repo_name,
                self.pr_number,
                summary
            )
            
            print("Code review completed successfully")
            
        except Exception as e:
            print(f"Error in code review process: {e}")
            raise

    async def _process_change(self, change: CodeChange) -> None:
        """Process a single code change.
        
        Args:
            change: Code change to process
        """
        try:
            # Format context for review
            context_lines = []
            for line_num in sorted(change.context.keys()):
                marker = " [CHANGED] " if line_num == change.line_number else " "
                context_lines.append(f"{line_num}:{marker}{change.context[line_num]}")
            
            context_str = "\n".join(context_lines)
            print(f"Reviewing {change.path} at line {change.line_number}")
            
            # TODO: Implement AI review logic here
            # For now, we'll just add a placeholder review
            reviews = [{
                "type": "suggestion",
                "severity": "low",
                "line": change.line_number,
                "message": "This is a placeholder review comment"
            }]
            
            # Process reviews
            comments = []
            for review in reviews:
                if review["line"] != change.line_number:
                    print(f"Skipping review for invalid line number: {review['line']}")
                    continue

                self.stats.update_stats(
                    review["type"],
                    review["severity"],
                    review["message"],
                    change.path,
                    review["line"]
                )
                
                comments.append({
                    **review,
                    "path": change.path,
                    "line": review["line"],
                    "message": review["message"]
                })

            # Merge and post comments
            merged_comments = self._merge_comments(comments)
            for comment in merged_comments:
                if self._find_existing_comment(comment):
                    print(f"Skipping duplicate comment for {comment['path']}:{comment['line']}")
                    continue

                await self.github.create_review_comment(
                    self.repo_owner,
                    self.repo_name,
                    self.pr_number,
                    os.environ.get("GITHUB_SHA", "HEAD"),
                    comment["path"],
                    comment["line"],
                    comment["body"]
                )
                
        except Exception as e:
            print(f"Error processing change in {change.path}:{change.line_number}: {e}")

async def main():
    """Main entry point for code review."""
    try:
        reviewer = CodeReviewer(
            github_token=os.environ["GITHUB_TOKEN"],
            repo_owner=os.environ["GITHUB_REPOSITORY_OWNER"],
            repo_name=os.environ["GITHUB_REPOSITORY"].split("/")[1],
            pr_number=int(os.environ["PR_NUMBER"]),
            base_branch=os.environ.get("BASE_BRANCH", "origin/main")
        )
        await reviewer.review_changes()
        
    except Exception as e:
        print(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main()) 