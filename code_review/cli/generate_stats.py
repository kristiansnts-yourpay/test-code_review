import argparse
import json
import sys
from typing import Dict

from code_review.stats.review_stats import ReviewStats

def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Generate statistics from code review results')
    parser.add_argument('review_file', help='JSON file containing the AI review')
    parser.add_argument('--output', '-o', help='Output file for statistics (default: stdout)')
    parser.add_argument('--format', choices=['text', 'json', 'markdown'], default='markdown',
                       help='Output format (default: markdown)')
    return parser.parse_args()

def load_review_data(review_file: str) -> Dict:
    """Load and validate review data from file."""
    try:
        with open(review_file, 'r') as f:
            review_data = json.load(f)
        
        if "error" in review_data:
            print(f"Error from API: {review_data['error']['message']}", file=sys.stderr)
            sys.exit(1)
        
        if "choices" not in review_data or not review_data["choices"]:
            print("No review content found in the response", file=sys.stderr)
            sys.exit(1)
        
        return review_data
    except FileNotFoundError:
        print(f"Review file not found: {review_file}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Invalid JSON in review file: {review_file}", file=sys.stderr)
        sys.exit(1)

def format_text_stats(stats: ReviewStats) -> str:
    """Format statistics as plain text."""
    total_issues = sum(stats.stats.values())
    
    output = "Code Review Statistics\n"
    output += "===================\n\n"
    output += f"Total issues found: {total_issues}\n"
    output += f"High severity issues: {len(stats.high_severity_issues)}\n"
    output += f"Type safety issues: {stats.stats['type_safety_issues']}\n"
    output += f"Architecture issues: {stats.stats['architecture_issues']}\n"
    output += f"Security concerns: {stats.stats['security_issues']}\n"
    output += f"Performance issues: {stats.stats['performance_issues']}\n"
    output += f"Readability improvements: {stats.stats['readability_issues']}\n"
    output += f"Suggestions: {stats.stats['suggestions']}\n"
    output += f"Good patterns identified: {stats.stats['good_patterns']}\n"
    
    if stats.high_severity_issues:
        output += "\nHigh Priority Issues:\n"
        for issue in stats.high_severity_issues:
            output += f"- {issue['type'].upper()}: {issue['message']} ({issue['file']}:{issue['line']})\n"
    
    return output

def format_json_stats(stats: ReviewStats) -> str:
    """Format statistics as JSON."""
    return json.dumps({
        'statistics': stats.stats,
        'high_severity_issues': stats.high_severity_issues,
        'issues_by_type': stats.issues_by_type
    }, indent=2)

def main():
    args = parse_args()
    review_data = load_review_data(args.review_file)
    
    # Initialize stats tracker
    stats = ReviewStats()
    
    # Get review content
    review_content = review_data["choices"][0]["message"]["content"]
    
    # Process review content and update stats
    sections = review_content.split('\n\n')
    for section in sections:
        # Extract type and severity using regex
        import re
        type_match = re.search(r'Type:\s*\(([\w-]+)\)', section)
        severity_match = re.search(r'Severity:\s*\((high|medium|low)\)', section)
        line_match = re.search(r'Line:\s*(\d+)', section)
        file_match = re.search(r'File:\s*([^\n]+)', section)
        
        if all([type_match, severity_match, line_match, file_match]):
            stats.update_stats(
                type_match.group(1),
                severity_match.group(1),
                section,
                file_match.group(1).strip(),
                int(line_match.group(1))
            )
    
    # Generate output in requested format
    if args.format == 'json':
        output = format_json_stats(stats)
    elif args.format == 'text':
        output = format_text_stats(stats)
    else:  # markdown
        output = stats.generate_summary()
    
    # Write output
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
    else:
        print(output)

if __name__ == "__main__":
    main() 