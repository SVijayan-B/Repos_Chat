import os

ALLOWED_EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go", ".rs", ".cpp", ".md", ".yaml", ".toml", ".json"}
HIGH_PRIORITY_PATTERNS = {"readme.md", "requirements.txt", "package.json", "pyproject.toml", "setup.py", "docker-compose.yml"}
HIGH_PRIORITY_DIRS = ["src/", "app/", "backend/", "frontend/", "api/", "services/", "models/"]
IGNORE_COMPLETELY_PATTERNS = [".git/", "cache/", "lock", ".min.js", "package-lock.json", "yarn.lock"]

def should_ignore(path: str) -> bool:
    path_lower = path.lower()
    if any(pat in path_lower for pat in IGNORE_COMPLETELY_PATTERNS):
        return True
    _, ext = os.path.splitext(path_lower)
    return ext not in ALLOWED_EXTENSIONS

def get_file_priority(path: str) -> str:
    path_lower = path.lower()
    if os.path.basename(path_lower) in HIGH_PRIORITY_PATTERNS:
        return "High"
    if any(d in path_lower for d in HIGH_PRIORITY_DIRS):
        return "High"
    return "Low"