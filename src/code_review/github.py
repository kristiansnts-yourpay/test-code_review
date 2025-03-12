import requests
from typing import Optional, Dict, Any, Union

class GitHubAPI:
    def __init__(self, token: str):
        self.token = token
        self.base_url = 'https://api.github.com'
        self.session = requests.Session()
        self.session.headers.update({
            'Authorization': f'Bearer {token}',
            'User-Agent': 'OpenRouter-Code-Review-Bot',
            'Accept': 'application/vnd.github.v3+json'
        })

    def make_request(self, method: str, path: str, data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Any:
        url = f'{self.base_url}{path}'
        request_headers = {}
        
        if headers:
            request_headers.update(headers)
            
        try:
            response = self.session.request(method, url, json=data, headers=request_headers)
            response.raise_for_status()
            return response.json() if response.text else None
        except requests.exceptions.RequestException as e:
            raise Exception(f'GitHub API request failed: {str(e)}')

    def get_pull_request(self, owner: str, repo: str, pr_number: Union[str, int]) -> Dict:
        path = f'/repos/{owner}/{repo}/pulls/{pr_number}'
        return self.make_request('GET', path)

    async def create_review_comment(self, owner: str, repo: str, pr_number: Union[str, int], 
                                  commit_id: str, path: str, line: int, body: str) -> Dict:
        try:
            pr = self.get_pull_request(owner, repo, pr_number)
            head_sha = pr['head']['sha']

            review_path = f'/repos/{owner}/{repo}/pulls/{pr_number}/comments'
            return self.make_request('POST', review_path, {
                'body': body,
                'commit_id': head_sha,
                'path': path,
                'position': line,
                'line': line,
                'side': 'RIGHT'
            })
        except Exception as error:
            if getattr(error, 'status_code', None) == 422 or getattr(getattr(error, 'response', None), 'status_code', None) == 422:
                print('Invalid position parameter detected, retrying with modified payload...')
                return self.make_request('POST', review_path, {
                    'body': body,
                    'commit_id': head_sha,
                    'path': path,
                    'line': line,
                    'side': 'RIGHT'
                })
            print('Error creating review comment:', error)
            raise error

    def post_comment(self, owner: str, repo: str, pr_number: Union[str, int], body: str) -> Dict:
        path = f'/repos/{owner}/{repo}/issues/{pr_number}/comments'
        return self.make_request('POST', path, {'body': body})

    def create_review(self, owner: str, repo: str, pr_number: Union[str, int], comments: list, body: str) -> Dict:
        path = f'/repos/{owner}/{repo}/pulls/{pr_number}/reviews'
        return self.make_request('POST', path, {
            'body': body,
            'event': 'COMMENT',
            'comments': comments
        })

    def get_pull_request_diff(self, owner: str, repo: str, pr_number: Union[str, int]) -> str:
        path = f'/repos/{owner}/{repo}/pulls/{pr_number}'
        headers = {'Accept': 'application/vnd.github.v3.diff'}
        return self.make_request('GET', path, headers=headers)

    def update_review_comment(self, owner: str, repo: str, comment_id: Union[str, int], body: str) -> Dict:
        path = f'/repos/{owner}/{repo}/pulls/comments/{comment_id}'
        return self.make_request('PATCH', path, {'body': body})

    def get_existing_comments(self, owner: str, repo: str, pr_number: Union[str, int]) -> list:
        path = f'/repos/{owner}/{repo}/pulls/{pr_number}/comments'
        return self.make_request('GET', path) 