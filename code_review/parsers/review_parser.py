import re
from typing import List, Dict, Optional

class ReviewParser:
    @staticmethod
    def process_code_suggestions(content: str, file_changes: Optional[Dict] = None) -> str:
        """Process review content to convert code blocks to GitHub suggested changes format."""
        pattern = r'```([a-zA-Z0-9_+-]+)(?::([^\n]+))?\n(.*?)\n```'
        correct_pattern = r'#\s*Correct:\s*\n(.*?)(?=\n\n|$)'
        
        def replacement(match):
            language = match.group(1) or ""
            file_path = match.group(2) if match.group(2) else None
            code = match.group(3)
            
            suggestion_indicators = [
                "should be", "change to", "replace with", "instead of", 
                "suggestion", "recommended", "fix", "correct", "improve"
            ]
            
            context_start = max(0, content.find(match.group(0)) - 300)
            context_end = content.find(match.group(0))
            context = content[context_start:context_end].lower()
            
            is_suggestion = any(indicator in context for indicator in suggestion_indicators)
            
            correct_match = re.search(correct_pattern, code, re.DOTALL)
            if correct_match:
                code = correct_match.group(1).strip()
                is_suggestion = True
            
            if file_path or is_suggestion:
                prefix = f"In `{file_path}`:\n" if file_path else ""
                return f"{prefix}```suggestion\n{code}\n```"
            else:
                return f"```{language}\n{code}\n```"
        
        processed_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        
        if processed_content != content:
            processed_content = (
                "## AI Code Review\n\n"
                "> Note: This review includes suggested code changes that can be directly applied.\n\n"
                + processed_content
            )
        
        return processed_content

    @staticmethod
    def extract_inline_comments(content: str, file_changes: Dict) -> List[Dict]:
        """Extract comments that should be posted inline on specific lines of code."""
        comments = []
        
        # File patterns for matching
        file_patterns = [
            r'(?:In|At|File)\s+`?([^:`\s]+)`?(?:\s+\(line\s+(\d+)\)|:(\d+))(?:\s*-\s*(\d+))?',
            r'`?([^:`\s]+)`?:(\d+)(?:\s*-\s*(\d+))?:',
        ]
        
        sections = re.split(r'\n\s*\n', content)
        
        for section in sections:
            ReviewParser._process_section(section, file_patterns, file_changes, comments)
            
        if not comments:
            ReviewParser._process_code_blocks(content, file_changes, comments)
        
        return comments

    @staticmethod
    def _process_section(section: str, file_patterns: List[str], file_changes: Dict, comments: List[Dict]) -> None:
        """Process a section of content to find inline comments."""
        for pattern in file_patterns:
            matches = re.finditer(pattern, section, re.IGNORECASE)
            for match in matches:
                file_path = match.group(1)
                line_num = None
                for i in range(2, 5):
                    if match.group(i) and not line_num:
                        line_num = int(match.group(i))
                
                if file_path and line_num and file_path in file_changes:
                    comment_text = section[match.end():].strip()
                    if comment_text:
                        comments.append({
                            'path': file_path,
                            'line': line_num,
                            'body': comment_text
                        })

    @staticmethod
    def _process_code_blocks(content: str, file_changes: Dict, comments: List[Dict]) -> None:
        """Process code blocks to find inline comments."""
        code_block_pattern = r'```([a-zA-Z0-9_+-]+)(?::([^\n]+))?\n(.*?)\n```'
        matches = re.finditer(code_block_pattern, content, flags=re.DOTALL)
        for match in matches:
            file_path = match.group(2)
            if file_path and file_path in file_changes:
                start_pos = max(0, content.rfind('\n\n', 0, match.start()))
                context = content[start_pos:match.start()].strip()
                if context:
                    line_match = re.search(r'line\s+(\d+)', context, re.IGNORECASE)
                    if line_match:
                        line_num = int(line_match.group(1))
                        comments.append({
                            'path': file_path,
                            'line': line_num,
                            'body': context
                        }) 