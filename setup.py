from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="ai-code-reviewer",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="AI-powered code review tool using OpenRouter API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/ai-code-reviewer",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.11",
    install_requires=[
        "requests>=2.31.0",
        "parse-diff>=0.7.1",
        "minimatch>=0.0.5",
        "aiohttp>=3.9.0",  # For async HTTP requests
    ],
    entry_points={
        "console_scripts": [
            "ai-review=code_review.main:main",
        ],
    },
    package_data={
        "code_review": ["code_review_guidelines/*.json"],
    },
) 