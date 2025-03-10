from setuptools import setup, find_packages

setup(
    name="code-review",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyGithub",
        "requests"
    ],
    entry_points={
        'console_scripts': [
            'code-review=code_review.cli.post_comments:main',
        ],
    },
) 