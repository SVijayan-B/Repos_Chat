import networkx as nx
import os
import logging
from typing import List, Dict, Any, Tuple, Set, Optional

logger = logging.getLogger(__name__)

class GraphBuilder:
    @staticmethod
    def resolve_import_to_file(import_str: str, current_file: str, all_files: Set[str]) -> Optional[str]:
        """
        Attempts to resolve an import string to a file path present in all_files.
        Handles python dots, js relative paths, etc.
        """
        if not import_str:
            return None
            
        import_clean = import_str.replace("'", "").replace('"', "").strip()
        
        # 1. Try exact matching (e.g., relative import: "./utils" or "../services/auth")
        if import_clean.startswith("."):
            current_dir = os.path.dirname(current_file)
            # Resolve relative parts
            resolved_rel = os.path.normpath(os.path.join(current_dir, import_clean)).replace("\\", "/")
            
            # Check combinations with extensions
            for ext in [".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cpp"]:
                if f"{resolved_rel}{ext}" in all_files:
                    return f"{resolved_rel}{ext}"
                if f"{resolved_rel}/index{ext}" in all_files:
                    return f"{resolved_rel}/index{ext}"
                # Go package imports or Java package imports
                if resolved_rel in all_files:
                    return resolved_rel

        # 2. Try python dot notation (e.g., "app.models" or "api.routes.auth")
        dot_path = import_clean.replace(".", "/")
        for file_path in all_files:
            # Check if file_path ends with dot_path + extension or dot_path + /__init__.py
            for ext in [".py", "/__init__.py"]:
                target_suffix = f"{dot_path}{ext}"
                if file_path.endswith(target_suffix):
                    return file_path
                    
        # 3. Simple substring match (fallback for external/relative packages, like "auth" matching "src/utils/auth.py")
        import_parts = import_clean.split("/")
        last_part = import_parts[-1]
        for file_path in all_files:
            file_name_no_ext, _ = os.path.splitext(os.path.basename(file_path))
            if file_name_no_ext == last_part:
                return file_path
                
        return None

    def build_graph(self, repo_files: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> nx.DiGraph:
        """
        Builds a NetworkX DiGraph representing the codebase dependencies.
        Nodes are file paths. Edges are imports.
        """
        graph = nx.DiGraph()
        all_paths = {f["path"] for f in repo_files}
        
        # Add all files as nodes
        for file_path in all_paths:
            graph.add_node(file_path, type="file")

        # Trace dependencies using chunk imports
        for chunk in chunks:
            file_path = chunk["file"]
            imports = chunk.get("imports", [])
            
            for imp in imports:
                resolved_target = self.resolve_import_to_file(imp, file_path, all_paths)
                if resolved_target and resolved_target != file_path:
                    # Add edge: source imports target (directional arrow goes from source to target)
                    graph.add_edge(file_path, resolved_target, type="import")
                    logger.debug(f"Resolved edge: {file_path} -> {resolved_target} via '{imp}'")
                    
        return graph

    def get_neighbors(self, graph: nx.DiGraph, file_paths: List[str], depth: int = 1) -> Set[str]:
        """
        Finds all neighboring files (both importing and imported by) up to a certain depth.
        """
        visited = set(file_paths)
        current_layer = set(file_paths)
        
        for _ in range(depth):
            next_layer = set()
            for node in current_layer:
                if node in graph:
                    # Outgoing imports (files this node depends on)
                    for neighbor in graph.successors(node):
                        if neighbor not in visited:
                            next_layer.add(neighbor)
                            visited.add(neighbor)
                    # Incoming imports (files depending on this node)
                    for neighbor in graph.predecessors(node):
                        if neighbor not in visited:
                            next_layer.add(neighbor)
                            visited.add(neighbor)
            current_layer = next_layer
            if not current_layer:
                break
                
        return visited
