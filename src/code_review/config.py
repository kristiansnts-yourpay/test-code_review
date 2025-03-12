"""Configuration settings for the code review system."""

import json
import os
from pathlib import Path
from typing import Dict, Any

from .emoji_config import EMOJI_CONFIG

def load_guidelines() -> Dict[str, str]:
    """Load language-specific review guidelines from JSON file."""
    guidelines_path = Path(__file__).parent.parent.parent / 'code_review_guidelines' / 'guidelines.json'
    try:
        with open(guidelines_path, 'r') as f:
            guidelines_data = json.load(f)
            return {item['language']: item['content'] for item in guidelines_data}
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Warning: Could not load guidelines.json: {e}")
        return {}

def get_review_prompt(file_path: str, guidelines: Dict[str, str]) -> str:
    """Get the appropriate review prompt based on file extension."""
    ext = file_path.split('.')[-1].lower()
    language_map = {
        'py': 'python',
        'php': 'php',
        'js': 'javascript',
        'ts': 'typescript',
        'jsx': 'javascript',
        'tsx': 'typescript'
    }
    
    language = language_map.get(ext)
    if language and language in guidelines:
        return guidelines[language]
    
    # Default prompt if no language-specific guideline is found
    return """Review the code changes and provide specific, actionable feedback. Focus on:
1. Code quality and readability
2. Performance implications
3. Security concerns
4. Best practices
5. Potential bugs or issues

Provide specific suggestions for improvements."""

REVIEW_CONFIG = {
    'emojis': EMOJI_CONFIG,
    'concurrency_limit': int(os.getenv('CONCURRENCY_LIMIT', '3')),
    'max_file_size': int(os.getenv('MAX_FILE_SIZE', '500')) * 1024,  # Default 500KB
    'guidelines': load_guidelines(),
    'get_review_prompt': get_review_prompt
} 