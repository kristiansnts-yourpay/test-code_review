class ReviewStats:
    def __init__(self):
        self.stats = {
            "type_safety_issues": 0,
            "architecture_issues": 0,
            "readability_issues": 0,
            "security_issues": 0,
            "performance_issues": 0,
            "suggestions": 0,
            "good_patterns": 0,
            "blocking_issues": 0
        }
        self.issues_by_type = {}
        self.high_severity_issues = []
        
    def update_stats(self, type_name, severity, message, file, line):
        """Update statistics based on issue type."""
        # Update count based on type
        type_key = f"{type_name}_issues"
        if type_key in self.stats:
            self.stats[type_key] += 1
        elif type_name == "suggestion":
            self.stats["suggestions"] += 1
        elif type_name == "good-practice":
            self.stats["good_patterns"] += 1
            
        # Track high severity issues
        if severity == "high":
            self.high_severity_issues.append({
                "type": type_name,
                "message": message,
                "file": file,
                "line": line
            })
            
        # Group issues by type
        if type_name not in self.issues_by_type:
            self.issues_by_type[type_name] = []
            
        self.issues_by_type[type_name].append({
            "severity": severity,
            "message": message,
            "file": file,
            "line": line
        })
        
    def generate_summary(self):
        """Generate a markdown summary of the review."""
        total_issues = sum(self.stats.values())
        
        summary = "## 🔍 Code Review Summary\n\n"
        
        # Overall statistics
        summary += "### 📊 Overall Statistics\n"
        summary += f"- Total issues found: {total_issues}\n"
        summary += f"- High severity issues: {len(self.high_severity_issues)}\n"
        summary += f"- Type safety issues: {self.stats['type_safety_issues']}\n"
        summary += f"- Architecture issues: {self.stats['architecture_issues']}\n"
        summary += f"- Security concerns: {self.stats['security_issues']}\n"
        summary += f"- Performance issues: {self.stats['performance_issues']}\n"
        summary += f"- Readability improvements: {self.stats['readability_issues']}\n"
        summary += f"- Suggestions: {self.stats['suggestions']}\n"
        summary += f"- Good patterns identified: {self.stats['good_patterns']}\n\n"
        
        # High severity issues section
        if self.high_severity_issues:
            summary += "### ❗ High Priority Issues\n"
            for issue in self.high_severity_issues:
                summary += f"- {issue['type'].upper()}: {issue['message']} ({issue['file']}:{issue['line']})\n"
            summary += "\n"
            
        # Detailed breakdown by type
        summary += "### 📝 Detailed Breakdown\n"
        for type_name, issues in self.issues_by_type.items():
            if issues:
                summary += f"\n#### {type_name.upper()}\n"
                
                # Group by severity
                by_severity = {"high": [], "medium": [], "low": []}
                for issue in issues:
                    by_severity[issue["severity"]].append(issue)
                    
                for severity in ["high", "medium", "low"]:
                    if by_severity[severity]:
                        summary += f"\n**{severity.upper()}**:\n"
                        for issue in by_severity[severity]:
                            summary += f"- {issue['message']} ({issue['file']}:{issue['line']})\n"
                            
        return summary
