"""Code review package for automated code analysis and feedback."""

from .main import CodeReviewer, main
from .stats import ReviewStats
from .config import REVIEW_CONFIG

__version__ = "1.0.0"
__all__ = ["CodeReviewer", "ReviewStats", "REVIEW_CONFIG", "main"] 