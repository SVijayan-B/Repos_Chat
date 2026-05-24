import logging
import networkx as nx
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

    async def retrieve(self, repo_id: int, query: str, top_k: int = 3) -> dict:
        qv = self.embedding_generator.get_embedding(query)
        stmt = select(Chunk).join(File).where(File.repository_id == repo_id)
        res = await self.db.execute(stmt)
        chunks = res.scalars().all()
        
        # Internal ranking engine
        def score(c):
            if not c.embedding: return 0.0
            return sum(x*y for x,y in zip(c.embedding, qv))
            
        matched = sorted(chunks, key=score, reverse=True)[:top_k]
        return {"chunks": [{"file_path": c.file_path, "symbol_name": c.symbol_name, "content": c.content} for c in matched], "graph_neighbors": []}