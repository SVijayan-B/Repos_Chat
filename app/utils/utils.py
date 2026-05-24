import logging
import networkx as nx
from typing import List, Dict, Any, Set
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.db_models import Chunk, GraphEdge, File
from app.embeddings.generator import EmbeddingGenerator
from app.graph.builder import GraphBuilder

logger = logging.getLogger(__name__)

class HybridRetrieval:
    def __init__(self, db: AsyncSession, embedding_generator: EmbeddingGenerator):
        self.db = db
        self.embedding_generator = embedding_generator
        self.graph_builder = GraphBuilder()

    async def retrieve(
        self,
        repo_id: int,
        query: str,
        top_k: int = 5,
        graph_depth: int = 1
    ) -> Dict[str, Any]:
        """
        Runs hybrid retrieval:
        1. Semantic vector search in PostgreSQL (pgvector).
        2. Rehydrates the NetworkX dependency graph.
        3. Traverses the graph to expand context (retrieving neighboring file contents).
        4. Synthesizes and returns context chunks.
        """
        logger.info(f"Running hybrid retrieval for query: '{query}'")
        
        # 1. Semantic search
        query_vector = self.embedding_generator.get_embedding(query)
        
        # Select chunks belonging to files in the repository
        stmt = (
            select(Chunk)
            .join(File)
            .where(File.repository_id == repo_id)
        )
        result = await self.db.execute(stmt)
        all_chunks = result.scalars().all()
        
        # Calculate cosine similarity in Python using numpy
        import numpy as np
        
        scored_chunks = []
        for chunk in all_chunks:
            if chunk.embedding:
                try:
                    # chunk.embedding is stored as a JSON list of floats
                    chunk_vec = np.array(chunk.embedding, dtype=np.float32)
                    q_vec = np.array(query_vector, dtype=np.float32)
                    
                    # Cosine similarity
                    norm_c = np.linalg.norm(chunk_vec)
                    norm_q = np.linalg.norm(q_vec)
                    if norm_c > 0 and norm_q > 0:
                        sim = np.dot(chunk_vec, q_vec) / (norm_c * norm_q)
                    else:
                        sim = 0.0
                    scored_chunks.append((sim, chunk))
                except Exception as ex:
                    logger.error(f"Error computing similarity for chunk {chunk.id}: {ex}")
                    scored_chunks.append((0.0, chunk))
            else:
                scored_chunks.append((0.0, chunk))
                
        # Sort by similarity descending
        scored_chunks.sort(key=lambda x: x[0], reverse=True)
        matched_chunks = [item[1] for item in scored_chunks[:top_k]]
        
        if not matched_chunks:
            logger.warning("No semantic matches found in database.")
            return {"chunks": [], "files_context": [], "graph_neighbors": []}

        # Collect paths from semantic matches
        matched_paths = list({c.file_path for c in matched_chunks})
        logger.info(f"Semantic match found paths: {matched_paths}")

        # 2. Rehydrate the NetworkX graph from database
        graph_stmt = select(GraphEdge).where(GraphEdge.repository_id == repo_id)
        graph_result = await self.db.execute(graph_stmt)
        edges = graph_result.scalars().all()
        
        repo_graph = nx.DiGraph()
        # Add matches as base nodes
        for path in matched_paths:
            repo_graph.add_node(path)
            
        for edge in edges:
            repo_graph.add_edge(edge.source, edge.target, type=edge.type)

        # 3. Graph expansion to find import neighbors
        expanded_paths = self.graph_builder.get_neighbors(repo_graph, matched_paths, depth=graph_depth)
        neighbor_paths = expanded_paths - set(matched_paths)
        logger.info(f"Graph expansion added neighbors: {list(neighbor_paths)}")

        # Fetch neighboring files content for context injection
        neighbor_files = []
        if neighbor_paths:
            neighbor_stmt = select(File).where(
                File.repository_id == repo_id,
                File.path.in_(list(neighbor_paths))
            )
            neighbor_result = await self.db.execute(neighbor_stmt)
            neighbor_files = neighbor_result.scalars().all()

        # Format chunks
        formatted_chunks = []
        for c in matched_chunks:
            formatted_chunks.append({
                "file_path": c.file_path,
                "symbol_name": c.symbol_name,
                "language": c.language,
                "content": c.content,
                "summary": c.summary,
                "imports": c.imports,
                "dependencies": c.dependencies
            })

        # Format neighboring files
        formatted_neighbors = []
        for f in neighbor_files:
            formatted_neighbors.append({
                "file_path": f.path,
                "content": f.content[:2000],  # truncate long neighbor contents to avoid bloating prompt
                "language": f.language
            })

        return {
            "chunks": formatted_chunks,
            "files_context": formatted_neighbors,
            "graph_neighbors": list(neighbor_paths)
        }
