from setuptools import setup, find_packages

setup(
    name="code-review",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyGithub",
        "requests",
        "parse-diff"
    ],
    entry_points={
        'console_scripts': [
            'code-review=code_review.cli.post_comments:main',
            'code-review-stats=code_review.cli.generate_stats:main',
        ],
    },
    package_data={
        'code_review': ['config/*.json'],
    },
) 