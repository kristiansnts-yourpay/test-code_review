import os
import json
import requests
from typing import List, Dict, Any, Optional
from minimatch import Minimatch
from .config import REVIEW_CONFIG

class OpenRouterAPI:
    def __init__(self, model: str = 'deepseek/deepseek-r1-distill-llama-70b:free'):
        self.base_url = 'https://openrouter.ai/api/v1'
        self.model = os.getenv('MODEL', model)
        self.file_pattern = os.getenv('FILE_PATTERN', '**/*.{js,jsx,ts,tsx,py,php}')
        self.api_key = os.getenv('OPENROUTER_API_KEY')
        
        if not self.api_key:
            raise ValueError('OPENROUTER_API_KEY environment variable is required')
        
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}',
            'HTTP-Referer': os.getenv('GITHUB_REPOSITORY', 'https://github.com'),
            'X-Title': 'GitHub Code Review'
        })

    def should_review_file(self, filename: str) -> bool:
        return Minimatch(self.file_pattern).match(filename)

    def make_request(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        url = f'{self.base_url}{endpoint}'
        try:
            response = self.session.post(url, json=data)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f'OpenRouter API request failed: {str(e)}')

    async def review_code(self, content: str, filename: str, changed_lines: List[int]) -> List[Dict[str, Any]]:
        if not self.should_review_file(filename):
            return []

        # Get language-specific review prompt
        review_prompt = REVIEW_CONFIG['get_review_prompt'](filename, REVIEW_CONFIG['guidelines'])

        prompt = f'''{review_prompt}

The code below shows:
- Each line starts with its EXACT line number followed by a colon
- Changed lines are marked with [CHANGED]
- You MUST use the EXACT line number shown at the start of the line in your response
- DO NOT use a line number unless you see it explicitly at the start of a line

Code to review from {filename}:

{content}

Response format (use EXACT line numbers from the start of lines):
[
  {{
    "line": <number_from_start_of_line>,
    "type": "code-quality" | "performance" | "security" | "best-practice" | "bug-risk" | "suggestion",
    "severity": "high" | "medium" | "low",
    "message": "<specific_issue_and_recommendation>"
  }}
]

Rules:
1. Only comment on [CHANGED] lines
2. Use EXACT line numbers shown at start of lines
3. Each line number must match one of: {json.dumps(changed_lines)}
4. Consider context when making suggestions
5. Be specific and actionable in recommendations
6. For security issues, use the exact line where dangerous code appears
7. For other multi-line issues, use the first line number where the issue appears

If no issues found, return: []'''

        try:
            response = await self.make_request('/chat/completions', {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': 'You are an expert code reviewer providing detailed, actionable feedback in JSON format.'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 2048,
                'top_p': 0.9
            })

            try:
                content = response['choices'][0]['message']['content']
                # Find the JSON array in the response
                import re
                json_match = re.search(r'\[[\s\S]*\]', content)
                
                if json_match:
                    reviews = json.loads(json_match.group(0))
                    return [
                        review for review in reviews
                        if review['line'] in changed_lines and review.get('type') and review.get('severity') and review.get('message')
                    ]
                else:
                    print('No valid JSON found in response')
                    return []
            except Exception as error:
                print('Error parsing OpenRouter review response:', error)
                return []
        except Exception as error:
            print('Error during code review:', error)
            return [] 