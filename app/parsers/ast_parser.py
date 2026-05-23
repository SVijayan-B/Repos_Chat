import os
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python, tree_sitter_javascript, tree_sitter_typescript, tree_sitter_go
    LANGUAGES = {
        "python": Language(tree_sitter_python.language()),
        "javascript": Language(tree_sitter_javascript.language()),
        "typescript": Language(tree_sitter_typescript.language_typescript())
    }
    HAS_TREE_SITTER = True
except Exception as e:
    HAS_TREE_SITTER = False
    LANGUAGES = {}
    logger.warning(f"Tree-sitter unavailable, falling back to regex: {e}")

EXT_MAPPING = {".py": "python", ".js": "javascript", ".ts": "typescript", ".tsx": "typescript"}