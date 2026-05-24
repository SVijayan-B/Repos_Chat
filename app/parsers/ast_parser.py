import os
import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try importing tree-sitter grammars. If any fails, we handle it gracefully.
try:
    from tree_sitter import Language, Parser
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_go
    import tree_sitter_rust
    import tree_sitter_java
    import tree_sitter_cpp
    
    LANGUAGES = {
        "python": Language(tree_sitter_python.language()),
        "javascript": Language(tree_sitter_javascript.language()),
        "typescript": Language(tree_sitter_typescript.language_typescript()),
        "tsx": Language(tree_sitter_typescript.language_tsx()),
        "go": Language(tree_sitter_go.language()),
        "rust": Language(tree_sitter_rust.language()),
        "java": Language(tree_sitter_java.language()),
        "cpp": Language(tree_sitter_cpp.language()),
    }
    HAS_TREE_SITTER = True
    logger.info("Tree-sitter and language grammars successfully loaded.")
except Exception as e:
    HAS_TREE_SITTER = False
    LANGUAGES = {}
    logger.warning(f"Tree-sitter initialization failed, falling back to regex parsing: {e}")

# Extension to language mapping
EXT_MAPPING = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".h": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
}

class ASTParser:
    def __init__(self):
        self.parsers = {}
        if HAS_TREE_SITTER:
            for lang_name, lang_obj in LANGUAGES.items():
                p = Parser(lang_obj)
                self.parsers[lang_name] = p

    def get_language(self, path: str) -> Optional[str]:
        _, ext = os.path.splitext(path.lower())
        return EXT_MAPPING.get(ext)

    def parse_file(self, path: str, content: str) -> List[Dict[str, Any]]:
        """Parses file content and returns a list of logical code chunks (symbols)."""
        lang = self.get_language(path)
        
        # If tree-sitter is available and language is supported, use AST parsing
        if HAS_TREE_SITTER and lang and lang in self.parsers:
            try:
                return self._parse_with_tree_sitter(path, content, lang)
            except Exception as e:
                logger.error(f"Tree-sitter failed for {path}, falling back to regex: {e}")
                return self._parse_with_regex(path, content, lang)
        else:
            # Fallback to regex-based/naive splitting (Markdown, YAML, JSON, etc. use this)
            return self._parse_with_regex(path, content, lang or "text")

    def _parse_with_tree_sitter(self, path: str, content: str, lang: str) -> List[Dict[str, Any]]:
        parser = self.parsers[lang]
        tree = parser.parse(bytes(content, "utf8"))
        root_node = tree.root_node
        
        chunks = []
        imports = []
        
        # 1. First pass: extract all imports at the module level
        self._extract_imports(root_node, content, lang, imports)
        
        # 2. Second pass: extract functions, classes, and methods
        symbols = []
        self._find_symbols(root_node, content, lang, symbols)
        
        # 3. Create chunks from symbols
        if not symbols:
            # If no symbols are found (e.g. script with only top-level code), treat the whole file as one chunk
            chunks.append({
                "file": path,
                "symbol": "module",
                "language": lang,
                "imports": imports,
                "dependencies": [],  # will be resolved at graph stage
                "content": content,
                "summary": f"Module implementation file: {path}"
            })
        else:
            for sym in symbols:
                # Extract references inside this symbol block to find internal dependencies
                dependencies = self._extract_dependencies(sym["node"], content)
                
                # Check for API routes or database access in the symbol content
                sym_content = content[sym["start"]:sym["end"]]
                
                chunks.append({
                    "file": path,
                    "symbol": sym["name"],
                    "language": lang,
                    "imports": imports,
                    "dependencies": list(dependencies),
                    "content": sym_content,
                    "summary": f"{sym['type'].capitalize()} {sym['name']} inside {path}"
                })
                
        return chunks

    def _extract_imports(self, node, content: str, lang: str, imports: List[str]):
        """Recursively traverse the AST to gather import statements."""
        # Language specific import node types
        import_types = {
            "python": ["import_statement", "import_from_statement"],
            "javascript": ["import_statement", "require_call"],
            "typescript": ["import_statement", "require_call"],
            "tsx": ["import_statement", "require_call"],
            "go": ["import_spec"],
            "rust": ["use_declaration"],
            "java": ["import_declaration"],
            "cpp": ["preproc_include"]
        }
        
        node_type = node.type
        if lang in import_types and node_type in import_types[lang]:
            text = content[node.start_byte:node.end_byte].strip()
            # Clean up the import statement to get the module name
            module_name = self._clean_import(text, lang)
            if module_name and module_name not in imports:
                imports.append(module_name)
                
        for child in node.children:
            self._extract_imports(child, content, lang, imports)

    def _clean_import(self, import_text: str, lang: str) -> str:
        """Extracts package/file names from import statements."""
        if lang == "python":
            # e.g., "from app.models import User" -> "app.models"
            # e.g., "import os" -> "os"
            m = re.match(r"^from\s+([\w\.]+)", import_text)
            if m:
                return m.group(1)
            m = re.match(r"^import\s+([\w\.,\s]+)", import_text)
            if m:
                return m.group(1).strip()
        elif lang in ("javascript", "typescript", "tsx"):
            # e.g., "import React from 'react'" -> "react"
            # e.g., "const fs = require('fs')" -> "fs"
            m = re.search(r"from\s+['\"]([^'\"]+)['\"]", import_text)
            if m:
                return m.group(1)
            m = re.search(r"require\(['\"]([^'\"]+)['\"]\)", import_text)
            if m:
                return m.group(1)
        elif lang == "go":
            # e.g., "import \"fmt\"" -> "fmt"
            m = re.search(r'"([^"]+)"', import_text)
            if m:
                return m.group(1)
        elif lang == "rust":
            # e.g., "use std::collections::HashMap;" -> "std::collections"
            m = re.match(r"^use\s+([\w:]+)", import_text)
            if m:
                parts = m.group(1).split("::")
                return "::".join(parts[:-1]) if len(parts) > 1 else parts[0]
        elif lang == "java":
            # e.g., "import java.util.List;" -> "java.util"
            m = re.match(r"^import\s+([\w\.]+)", import_text)
            if m:
                parts = m.group(1).split(".")
                return ".".join(parts[:-1]) if len(parts) > 1 else parts[0]
        elif lang == "cpp":
            # e.g., "#include <vector>" -> "vector"
            # e.g., "#include \"auth.h\"" -> "auth.h"
            m = re.match(r"^#include\s+[<\"]([^>\"]+)[>\"]", import_text)
            if m:
                return m.group(1)
        return import_text

    def _find_symbols(self, node, content: str, lang: str, symbols: List[Dict[str, Any]]):
        """Recursively search AST for class and function/method nodes."""
        node_type = node.type
        
        # Check node types
        is_symbol = False
        sym_type = ""
        sym_name = ""
        
        if lang == "python":
            if node_type == "class_definition":
                is_symbol, sym_type = True, "class"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownClass"
            elif node_type == "function_definition":
                is_symbol, sym_type = True, "function"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownFunc"
                
        elif lang in ("javascript", "typescript", "tsx"):
            if node_type in ("class_declaration", "class"):
                is_symbol, sym_type = True, "class"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownClass"
            elif node_type in ("function_declaration", "function"):
                is_symbol, sym_type = True, "function"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownFunc"
            elif node_type == "method_definition":
                is_symbol, sym_type = True, "method"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownMethod"
                
        elif lang == "go":
            if node_type == "function_declaration":
                is_symbol, sym_type = True, "function"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownFunc"
            elif node_type == "method_declaration":
                is_symbol, sym_type = True, "method"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownMethod"
                
        elif lang == "rust":
            if node_type == "function_item":
                is_symbol, sym_type = True, "function"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownFunc"
            elif node_type in ("struct_item", "enum_item", "trait_item"):
                is_symbol, sym_type = True, "struct"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownStruct"
                
        elif lang == "java":
            if node_type == "class_declaration":
                is_symbol, sym_type = True, "class"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownClass"
            elif node_type == "method_declaration":
                is_symbol, sym_type = True, "method"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownMethod"
                
        elif lang == "cpp":
            if node_type == "class_specifier":
                is_symbol, sym_type = True, "class"
                name_node = node.child_by_field_name("name")
                sym_name = content[name_node.start_byte:name_node.end_byte] if name_node else "UnknownClass"
            elif node_type == "function_definition":
                is_symbol, sym_type = True, "function"
                # C++ functions might be complex, let's find the declarator name
                declarator = node.child_by_field_name("declarator")
                if declarator:
                    sym_name = content[declarator.start_byte:declarator.end_byte]
                    # Clean C++ declarator names like "void MyClass::func()"
                    sym_name = re.sub(r'[\s\S]*::', '', sym_name)
                    sym_name = re.sub(r'\(.*?\)', '', sym_name).strip()
                else:
                    sym_name = "UnknownFunc"

        if is_symbol:
            symbols.append({
                "node": node,
                "type": sym_type,
                "name": sym_name,
                "start": node.start_byte,
                "end": node.end_byte
            })
            
            # Avoid traversing deeper if it's a function/method (keeps granularity high).
            # But let classes traverse deep so we can find their inner methods.
            if sym_type != "class":
                return

        for child in node.children:
            self._find_symbols(child, content, lang, symbols)

    def _extract_dependencies(self, node, content: str) -> List[str]:
        """Find identifiers or potential variable references to match dependencies."""
        deps = set()
        
        def traverse(n):
            if n.type == "identifier":
                val = content[n.start_byte:n.end_byte].strip()
                if len(val) > 2:  # Skip single character variable names
                    deps.add(val)
            for child in n.children:
                traverse(child)
                
        traverse(node)
        return list(deps)

    def _parse_with_regex(self, path: str, content: str, lang: str) -> List[Dict[str, Any]]:
        """Regex-based fallback for parsing files when tree-sitter is missing or fails."""
        # Simple logical block partition
        chunks = []
        filename = os.path.basename(path)
        
        # Look for class or function headers
        lines = content.splitlines()
        current_chunk = []
        current_symbol = "file_header"
        
        for i, line in enumerate(lines):
            # Check for python class/def, js function/class, etc.
            is_new_block = False
            symbol_name = ""
            
            if lang == "python":
                m = re.match(r"^\s*(class|def)\s+([\w_]+)", line)
                if m:
                    is_new_block = True
                    symbol_name = m.group(2)
            elif lang in ("javascript", "typescript", "tsx", "java", "cpp"):
                m = re.match(r"^\s*(class|function|async\s+function|public|private|void)\s+([\w_]+)", line)
                if m:
                    is_new_block = True
                    symbol_name = m.group(2)
            elif lang == "go":
                m = re.match(r"^func\s+([\w_]+)", line)
                if m:
                    is_new_block = True
                    symbol_name = m.group(1)
                else:
                    m = re.match(r"^func\s+\(\s*[\w_]+\s*\*?([\w_]+)\s*\)\s*([\w_]+)", line)
                    if m:
                        is_new_block = True
                        symbol_name = f"{m.group(1)}.{m.group(2)}"
            elif lang == "rust":
                m = re.match(r"^\s*(fn|struct|impl|trait|enum)\s+([\w_]+)", line)
                if m:
                    is_new_block = True
                    symbol_name = m.group(2)

            if is_new_block and current_chunk:
                # Save previous chunk
                chunks.append({
                    "file": path,
                    "symbol": current_symbol,
                    "language": lang,
                    "imports": self._regex_extract_imports(content, lang),
                    "dependencies": [],
                    "content": "\n".join(current_chunk),
                    "summary": f"Section {current_symbol} of {filename}"
                })
                current_chunk = []
                current_symbol = symbol_name
                
            current_chunk.append(line)
            
        # Add last chunk
        if current_chunk:
            chunks.append({
                "file": path,
                "symbol": current_symbol,
                "language": lang,
                "imports": self._regex_extract_imports(content, lang),
                "dependencies": [],
                "content": "\n".join(current_chunk),
                "summary": f"Section {current_symbol} of {filename}"
            })
            
        # If we have too many small chunks, combine them or keep them
        return chunks

    def _regex_extract_imports(self, content: str, lang: str) -> List[str]:
        imports = []
        if lang == "python":
            for m in re.finditer(r"^(?:import\s+([\w\.,\s]+)|from\s+([\w\.]+)\s+import)", content, re.MULTILINE):
                val = m.group(1) or m.group(2)
                if val:
                    imports.extend([v.strip() for v in val.split(",")])
        elif lang in ("javascript", "typescript", "tsx"):
            for m in re.finditer(r"(?:import\s+.*from\s+['\"]([^'\"]+)['\"]|require\(['\"]([^'\"]+)['\"]\))", content):
                val = m.group(1) or m.group(2)
                if val:
                    imports.append(val)
        return list(set(imports))
