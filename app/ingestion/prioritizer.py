import os
from typing import Tuple

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".md", ".yaml", ".toml", ".json"
}

HIGH_PRIORITY_PATTERNS = [
    "readme.md",
    "requirements.txt",
    "package.json",
    "pyproject.toml",
    "setup.py",
    "docker-compose.yml",
]

HIGH_PRIORITY_DIRS = [
    "src/", "app/", "backend/", "frontend/", "api/", "configs/", "services/", "models/", "controllers/"
]

LOW_PRIORITY_DIRS = [
    "tests/", "assets/", "images/", "videos/", "logs/", "dist/", "build/", "node_modules/"
]

IGNORE_COMPLETELY_PATTERNS = [
    ".git/", "cache/", "lock", ".min.js", "package-lock.json", "yarn.lock", "cargo.lock", "poetry.lock", "pnpm-lock.yaml"
]

def should_ignore(path: str) -> bool:
    """Determine if a file path should be ignored entirely."""
    path_lower = path.lower()
    
    # Check ignore patterns
    for pattern in IGNORE_COMPLETELY_PATTERNS:
        if pattern in path_lower:
            return True
            
    # Check extension
    _, ext = os.path.splitext(path_lower)
    if ext not in ALLOWED_EXTENSIONS:
        return True
        
    return False

def get_file_priority(path: str) -> str:
    """Classify the file priority as 'High' or 'Low'."""
    path_lower = path.lower()
    base_name = os.path.basename(path_lower)
    
    # 1. Exact matches for important config files
    if base_name in HIGH_PRIORITY_PATTERNS:
        return "High"
        
    # 2. Check if file is in high-priority directories
    for directory in HIGH_PRIORITY_DIRS:
        if directory in path_lower:
            return "High"
            
    # 3. Check if file is in low-priority directories
    for directory in LOW_PRIORITY_DIRS:
        if directory in path_lower:
            return "Low"
            
    # Default to High if it matches our allowed file types and isn't explicitly low priority
    return "High"
