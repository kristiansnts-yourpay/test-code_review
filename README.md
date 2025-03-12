# AI Code Reviewer

An AI-powered code review tool that automatically reviews pull requests using OpenRouter API.

## Features

- Language-specific code review guidelines
- Automatic PR comment creation
- Support for multiple programming languages (Python, PHP, JavaScript, TypeScript)
- Customizable review rules and emojis
- Asynchronous processing for better performance

## Installation

```bash
pip install ai-code-reviewer
```

## Usage

1. Set up required environment variables:
```bash
export GITHUB_TOKEN=your_token
export OPENROUTER_API_KEY=your_key
```

2. Add the GitHub Action to your repository by creating `.github/workflows/ai-reviewer.yml`

3. The reviewer will automatically run on pull requests.

## Configuration

You can customize the reviewer by:

1. Adding language-specific guidelines in `code_review_guidelines/guidelines.json`
2. Modifying emoji mappings in `emoji_config.py`
3. Adjusting environment variables:
   - `CONCURRENCY_LIMIT`: Number of concurrent reviews (default: 3)
   - `MAX_FILE_SIZE`: Maximum file size to review in KB (default: 500)
   - `FILE_PATTERN`: Files to review (default: `**/*.{js,jsx,ts,tsx,py,php}`)
   - `MODEL`: OpenRouter model to use (default: deepseek/deepseek-r1-distill-llama-70b:free)

## License

MIT License