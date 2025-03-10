"""Setup configuration for code review package."""
from setuptools import setup, find_packages

setup(
    name="code_review",
    version="1.0.0",
    description="A Python-based code review tool for automated analysis and feedback",
    author="Your Name",
    author_email="your.email@example.com",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "unidiff>=0.7.0",
        "aiohttp>=3.8.0",
        "typing-extensions>=4.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "code-review=code_review.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Quality Assurance",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 