"""Statistics tracking for code reviews."""
from collections import defaultdict
from typing import Dict, List
from .config import REVIEW_CONFIG

class ReviewStats:
    """Track statistics for code reviews."""
    
    def __init__(self):
        """Initialize review statistics."""
        self.stats = {
            "by_type": defaultdict(int),
            "by_severity": defaultdict(int),
            "by_file": defaultdict(lambda: defaultdict(list)),
            "total_issues": 0
        }

    def update_stats(
        self,
        review_type: str,
        severity: str,
        message: str,
        file_path: str,
        line: int
    ) -> None:
        """Update review statistics.
        
        Args:
            review_type: Type of review comment
            severity: Severity level
            message: Review message
            file_path: Path to the file
            line: Line number
        """
        self.stats["by_type"][review_type] += 1
        self.stats["by_severity"][severity] += 1
        self.stats["by_file"][file_path][severity].append({
            "line": line,
            "message": message,
            "type": review_type
        })
        self.stats["total_issues"] += 1

    def generate_summary(self) -> str:
        """Generate a markdown summary of review statistics.
        
        Returns:
            Formatted markdown summary
        """
        summary = ["## Code Review Summary\n"]

        # Add total issues
        summary.append(f"### Total Issues: {self.stats['total_issues']}\n")

        # Add breakdown by type
        summary.append("### Issues by Type\n")
        for review_type, count in self.stats["by_type"].items():
            emoji = REVIEW_CONFIG["emojis"].get(review_type, "💭")
            summary.append(f"- {emoji} {review_type.title()}: {count}")
        summary.append("")

        # Add breakdown by severity
        summary.append("### Issues by Severity\n")
        severity_emojis = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        for severity, count in self.stats["by_severity"].items():
            emoji = severity_emojis.get(severity, "⚪")
            summary.append(f"- {emoji} {severity.title()}: {count}")
        summary.append("")

        # Add file-specific breakdown
        summary.append("### Issues by File\n")
        for file_path, severities in self.stats["by_file"].items():
            summary.append(f"#### {file_path}\n")
            for severity, issues in severities.items():
                emoji = severity_emojis.get(severity, "⚪")
                summary.append(f"- {emoji} {severity.title()}: {len(issues)} issues")
            summary.append("")

        return "\n".join(summary) 