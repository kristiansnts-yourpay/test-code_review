import json
import os
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load the review configuration from JSON file."""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 
        "config", 
        "review_config.json"
    )
    
    with open(config_path, 'r') as f:
        return json.load(f)

# Singleton-like access to config
REVIEW_CONFIG = load_config() 