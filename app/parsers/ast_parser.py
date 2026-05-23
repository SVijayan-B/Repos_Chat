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

class ASTParser:
    def __init__(self):
        self.parsers = {}
        if HAS_TREE_SITTER:
            for lang, obj in LANGUAGES.items():
                p = Parser()
                p.set_language(obj)
                self.parsers[lang] = p

    def chunk_file(self, path: str, content: str) -> List[Dict[str, Any]]:
        _, ext = os.path.splitext(path.lower())
        lang = EXT_MAPPING.get(ext, "text")
        if lang == "text" or not HAS_TREE_SITTER or lang not in self.parsers:
            return self._regex_fallback_chunk(path, content, lang)
        return self._tree_sitter_chunk(path, content, lang)

    def _tree_sitter_chunk(self, path: str, content: str, lang: str) -> List[Dict[str, Any]]:
        parser = self.parsers[lang]
        tree = parser.parse(bytes(content, "utf8"))
        chunks = []
        query_str = "(class_definition) @class (function_definition) @func" if lang == "python" else "(class_definition) @class (function_declaration) @func"
        try:
            query = LANGUAGES[lang].query(query_str)
            captures = query.captures(tree.root_node)
            for node, tag in captures:
                code = content[node.start_byte:node.end_byte]
                chunks.append({
                    "file": path, "symbol": f"{tag}", "language": lang,
                    "imports": self._regex_extract_imports(code, lang), "dependencies": [],
                    "content": code, "summary": f"Extracted code segment from {os.path.basename(path)}"
                })
        except Exception:
            return self._regex_fallback_chunk(path, content, lang)
        return chunks if chunks else self._regex_fallback_chunk(path, content, lang)
    
    def _regex_fallback_chunk(self, path: str, content: str, lang: str) -> List[Dict[str, Any]]:
        filename = os.path.basename(path)
        return [{
            "file": path, "symbol": "global", "language": lang,
            "imports": self._regex_extract_imports(content, lang), "dependencies": [],
            "content": content, "summary": f"Complete code file text contents of {filename}"
        }]

    def _regex_extract_imports(self, content: str, lang: str) -> List[str]:
        imports = []
        if lang == "python":
            for m in re.finditer(r"^(?:import\s+([\w\.,\s]+)|from\s+([\w\.]+)\s+import)", content, re.MULTILINE):
                val = m.group(1) or m.group(2)
                if val: imports.extend([v.strip() for v in val.split(",")])
        return imports