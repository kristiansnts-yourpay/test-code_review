import json
import requests
import os

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
PR_NUMBER = os.getenv("PR_NUMBER")
REPO = os.getenv("GITHUB_REPOSITORY")

def post_review_comments():
    with open("review.json", "r") as file:
        review = json.load(file)
    
    comment_body = review.get("choices", [{}])[0].get("text", "No comments found.")

    url = f"https://api.github.com/repos/{REPO}/issues/{PR_NUMBER}/comments"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"body": comment_body}
    
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 201:
        print("Review posted successfully!")
    else:
        print("Failed to post review:", response.text)

if __name__ == "__main__":
    post_review_comments()
