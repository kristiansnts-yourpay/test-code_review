import json
import re
from typing import Dict, Optional, Set

class GuidelinesSelector:
    def __init__(self, guidelines_path: str = 'code_review_guidelines/guidelines.json'):
        self.guidelines_path = guidelines_path
        self.guidelines = self._load_guidelines()

    def _load_guidelines(self) -> list:
        """Load guidelines from JSON file."""
        try:
            with open(self.guidelines_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Guidelines file not found at {self.guidelines_path}")
            return []

    def _detect_file_types(self, diff_content: str) -> Set[str]:
        """Extract file extensions from diff content."""
        file_extensions = set()
        for line in diff_content.split('\n'):
            if line.startswith('+++') or line.startswith('---'):
                match = re.search(r'\.([\w]+)$', line)
                if match:
                    file_extensions.add(match.group(1))
        return file_extensions

    def select_guidelines(self, diff_content: str) -> Dict:
        """Select appropriate guidelines based on file types in diff."""
        file_extensions = self._detect_file_types(diff_content)
        print(f"File types detected: {', '.join(file_extensions)}")
        
        # Try to find matching guideline
        for guideline in self.guidelines:
            if guideline['language'] in file_extensions:
                print(f"Using guidelines for: {guideline['language']}")
                return guideline
        
        # Default to first guideline if available
        if self.guidelines:
            print(f"No matching guidelines found. Defaulting to: {self.guidelines[0]['language']}")
            return self.guidelines[0]
        
        # Fallback to default guideline
        print("No guidelines available. Using default system prompt.")
        return {
            "content": "You are an expert code reviewer and software engineer specializing in best practices, clean code, performance optimization, security, and maintainability. Analyze the following code changes and provide constructive feedback."
        }

    def create_review_payload(self, diff_content: str, model: str = "deepseek/deepseek-r1-distill-llama-70b:free") -> Dict:
        """Create the payload for the AI review API request."""
        guideline = self.select_guidelines(diff_content)
        
        review_instruction = """
When providing code examples, please use clear "Wrong" and "Correct" sections with explanatory comments:

# Wrong:
foo = long_function_name(var_one, var_two,
    var_three, var_four)

# Correct:
foo = long_function_name(
    var_one, var_two,
    var_three, var_four)
"""
        
        guideline_content = guideline["content"] + "\n\n" + review_instruction
        
        return {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": guideline_content
                },
                {
                    "role": "user",
                    "content": diff_content
                }
            ]
        } 