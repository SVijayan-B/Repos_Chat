import networkx as nx
import os
from typing import list, Dict, Any, Optional

class GraphBuilder:
    @staticmethod
    def resolve_import_to_file(import_str: str, current_file: str, all_files: set) -> Optional[str]:
        if not import_str: return None
        clean = import_str.strip()
        if clean.startswith("."):
            resolved = os.path.normpath(os.path.join(os.path.dirname(current_file), clean)).replace("\\", "/")
            for ext in [".py", ".js", ".ts"]:
                if f"{resolved}{ext}" in all_files: return f"{resolved}{ext}"
        for f in all_files:
            if clean.replace(".", "/") in f or f.startswith(clean): return f
        return None

    def build_dependency_graph(self, chunks: list, all_paths: list) -> nx.DiGraph:
        g = nx.DiGraph()
        path_set = set(all_paths)
        g.add_nodes_from(all_paths)
        for chunk in chunks:
            src = chunk["file"]
            for imp in chunk.get("imports", []):
                tgt = self.resolve_import_to_file(imp, src, path_set)
                if tgt and tgt != src:
                    g.add_edge(src, tgt, type="import")
        return g
    
    def get_neighbors(self, graph: nx.DiGraph, paths: list, depth: int = 1) -> set:
        visited = set(paths)
        layer = set(paths)
        for _ in range(depth):
            next_layer = set()
            for node in layer:
                if node in graph:
                    for nxt in list(graph.successors(node)) + list(graph.predecessors(node)):
                        if nxt not in visited:
                            next_layer.add(nxt)
                            visited.add(nxt)
            layer = next_layer
            if not layer: break
        return visited