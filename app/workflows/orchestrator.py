import logging
import asyncio
import json
from typing import Dict, Any, List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from sqlalchemy import select, delete
from app.database.session import SessionLocal
from app.models.db_models import Repository, File, Chunk, GraphEdge
from app.github.client import GitHubClient
from app.ingestion.prioritizer import should_ignore, get_file_priority
from app.parsers.ast_parser import ASTParser
from app.graph.builder import GraphBuilder
from app.embeddings.generator import EmbeddingGenerator
from app.architecture.summarizer import ArchitectureSummarizer
from app.retrieval.hybrid import HybridRetrieval
from app.llm.groq_client import GroqClient
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Define Ingestion State
class IngestionState(TypedDict):
    owner: str
    repo: str
    branch: str
    repo_id: Optional[int]
    tree: List[Dict[str, Any]]
    prioritized_files: List[Dict[str, Any]]
    fetched_files: List[Dict[str, Any]]
    chunks: List[Dict[str, Any]]
    architecture_summary: Dict[str, Any]
    progress: str

# Define Retrieval/Chat State
class ChatState(TypedDict):
    repo_id: int
    query: str
    explanation_mode: str  # beginner, intermediate, expert
    chat_history: List[Dict[str, str]]
    context: Dict[str, Any]
    answer: str

class WorkflowOrchestrator:
    def __init__(self):
        self.github_client = GitHubClient()
        self.ast_parser = ASTParser()
        self.graph_builder = GraphBuilder()
        self.embedding_generator = EmbeddingGenerator()
        self.groq_client = GroqClient()
        self.summarizer = ArchitectureSummarizer(self.groq_client)

    # ----------------------------------------------------
    # INGESTION WORKFLOW NODES
    # ----------------------------------------------------
    async def fetch_tree_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info(f"Node: Fetch Tree for {state['owner']}/{state['repo']}")
        tree_res = await self.github_client.get_tree(state["owner"], state["repo"], state["branch"])
        
        tree_files = []
        if tree_res and "tree" in tree_res:
            tree_files = tree_res["tree"]
            logger.info(f"Found {len(tree_files)} raw objects in repository tree.")
        else:
            logger.error("Failed to fetch repository tree or empty repository.")
            
        return {
            "tree": tree_files,
            "progress": f"Fetched repository tree. Found {len(tree_files)} objects."
        }

    async def prioritize_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Prioritize & Filter files")
        tree = state.get("tree", [])
        prioritized = []
        
        for item in tree:
            if item.get("type") == "blob":  # file
                path = item.get("path", "")
                if not should_ignore(path):
                    priority = get_file_priority(path)
                    prioritized.append({
                        "path": path,
                        "priority": priority,
                        "size": item.get("size", 0)
                    })
                    
        # Sort prioritized files: High priority first
        prioritized.sort(key=lambda x: x["priority"] == "Low")
        logger.info(f"Filtered down to {len(prioritized)} processable files.")
        
        return {
            "prioritized_files": prioritized,
            "progress": f"Filtered repository files. {len(prioritized)} files selected for ingestion."
        }

    async def fetch_contents_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Async Fetch Contents")
        files_to_fetch = state.get("prioritized_files", [])
        owner = state["owner"]
        repo = state["repo"]
        branch = state["branch"]
        
        fetched = []
        # Concurrency limit using Semaphore
        sem = asyncio.Semaphore(settings.concurrency_limit)
        
        async def fetch_one(f):
            async with sem:
                # Check file size to avoid processing massive binary or configuration files
                if f["size"] > settings.max_file_size_kb * 1024:
                    logger.debug(f"Skipping large file: {f['path']} ({f['size']} bytes)")
                    return
                
                content = await self.github_client.get_file_content(owner, repo, branch, f["path"])
                if content is not None:
                    fetched.append({
                        "path": f["path"],
                        "content": content,
                        "priority": f["priority"]
                    })

        # Run fetch tasks concurrently
        tasks = [fetch_one(f) for f in files_to_fetch]
        await asyncio.gather(*tasks)
        logger.info(f"Successfully fetched {len(fetched)} files.")
        
        return {
            "fetched_files": fetched,
            "progress": f"Fetched {len(fetched)} files asynchronously."
        }

    async def parse_ast_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Parse AST")
        fetched = state.get("fetched_files", [])
        all_chunks = []
        
        for f in fetched:
            # Parse code and generate chunks (functions, classes, etc.)
            chunks = self.ast_parser.parse_file(f["path"], f["content"])
            # Inject priorities from files
            for chunk in chunks:
                chunk["priority"] = f["priority"]
            all_chunks.extend(chunks)
            
        logger.info(f"Extracted {len(all_chunks)} logical symbol chunks from AST.")
        return {
            "chunks": all_chunks,
            "progress": f"Parsed AST. Extracted {len(all_chunks)} code symbols/chunks."
        }

    async def generate_graph_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Generate Graph")
        fetched = state.get("fetched_files", [])
        chunks = state.get("chunks", [])
        
        # Build networkx graph
        graph = self.graph_builder.build_graph(fetched, chunks)
        
        # Convert graph edges to schema dictionary
        edges_to_save = []
        for u, v, d in graph.edges(data=True):
            edges_to_save.append({
                "source": u,
                "target": v,
                "type": d.get("type", "import")
            })
            
        logger.info(f"Built code relationship graph. Detected {len(edges_to_save)} edges.")
        return {
            "progress": f"Generated dependency graph with {len(edges_to_save)} imports.",
            "tree": state.get("tree"),  # retain
            "fetched_files": fetched,
            "chunks": chunks,
            "graph_edges": edges_to_save  # transient store in state
        }

    async def summarize_repo_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Summarize Repo")
        fetched_files = state.get("fetched_files", [])
        
        # Find README
        readme_content = ""
        for f in fetched_files:
            if f["path"].lower() == "readme.md":
                readme_content = f["content"]
                break
                
        # Get summaries of first 15 high-priority files to create a synthesis
        high_priority_summaries = []
        for f in fetched_files:
            if f["priority"] == "High" and f["path"].lower() != "readme.md":
                # Create a mini summary or use top lines as snippet
                snippet = f["content"][:600]
                high_priority_summaries.append({
                    "path": f["path"],
                    "summary": f"Content snippet:\n{snippet}"
                })
                
        # Generate JSON summary
        summary_report = await self.summarizer.generate_summary(
            state["owner"],
            state["repo"],
            state.get("prioritized_files", []),
            readme_content,
            high_priority_summaries
        )
        
        return {
            "architecture_summary": summary_report,
            "progress": "Generated architecture summary."
        }

    async def vector_store_node(self, state: IngestionState) -> Dict[str, Any]:
        logger.info("Node: Vector Store & DB Write")
        chunks = state.get("chunks", [])
        fetched_files = state.get("fetched_files", [])
        edges = state.get("graph_edges", [])
        summary = state.get("architecture_summary", {})
        
        async with SessionLocal() as db:
            # 1. Clean existing records for this repository to support re-indexing
            stmt = select(Repository).where(
                Repository.owner == state["owner"],
                Repository.name == state["repo"]
            )
            res = await db.execute(stmt)
            existing_repo = res.scalars().first()
            if existing_repo:
                logger.info(f"Re-indexing {state['owner']}/{state['repo']}. Removing old entries.")
                await db.delete(existing_repo)
                await db.commit()
            
            # 2. Save Repository
            repo_db = Repository(
                owner=state["owner"],
                name=state["repo"],
                default_branch=state["branch"],
                architecture_summary=json.dumps(summary)
            )
            db.add(repo_db)
            await db.flush()  # gets repo_db.id
            repo_id = repo_db.id

            # 3. Save Files
            file_map = {}
            for f in fetched_files:
                file_db = File(
                    repository_id=repo_id,
                    path=f["path"],
                    content=f["content"],
                    priority=f["priority"],
                    language=self.ast_parser.get_language(f["path"])
                )
                db.add(file_db)
                await db.flush()
                file_map[f["path"]] = file_db.id

            # 4. Generate embeddings and save Chunks in batches
            chunk_contents = [c["content"] for c in chunks]
            embeddings = []
            if chunk_contents:
                logger.info(f"Computing embeddings for {len(chunk_contents)} chunks...")
                embeddings = self.embedding_generator.get_embeddings_batch(chunk_contents)

            for i, c in enumerate(chunks):
                file_path = c["file"]
                file_id = file_map.get(file_path)
                if not file_id:
                    continue
                    
                chunk_db = Chunk(
                    file_id=file_id,
                    file_path=file_path,
                    symbol_name=c["symbol"],
                    language=c["language"],
                    imports=c["imports"],
                    dependencies=c["dependencies"],
                    content=c["content"],
                    summary=c["summary"],
                    embedding=embeddings[i] if i < len(embeddings) else None
                )
                db.add(chunk_db)

            # 5. Save Graph Edges
            for edge in edges:
                edge_db = GraphEdge(
                    repository_id=repo_id,
                    source=edge["source"],
                    target=edge["target"],
                    type=edge["type"]
                )
                db.add(edge_db)
                
            await db.commit()
            logger.info("Successfully persisted all repository structures and vectors in Postgres.")
            
        return {
            "repo_id": repo_id,
            "progress": "Repository ingestion, AST parsing, graph matching, and vector storage completed successfully."
        }

    # ----------------------------------------------------
    # CHAT WORKFLOW NODES
    # ----------------------------------------------------
    async def retrieve_node(self, state: ChatState) -> Dict[str, Any]:
        logger.info("Node: Chat Retrieval")
        async with SessionLocal() as db:
            retrieval = HybridRetrieval(db, self.embedding_generator)
            context = await retrieval.retrieve(state["repo_id"], state["query"])
            
        return {
            "context": context
        }

    async def reasoning_node(self, state: ChatState) -> Dict[str, Any]:
        logger.info("Node: Groq Reasoning")
        context = state.get("context", {})
        query = state["query"]
        history = state.get("chat_history", [])
        mode = state.get("explanation_mode", "intermediate")
        
        # 1. Rehydrate repo name/owner and architecture summary
        async with SessionLocal() as db:
            stmt = select(Repository).where(Repository.id == state["repo_id"])
            res = await db.execute(stmt)
            repo = res.scalars().first()
            repo_title = f"{repo.owner}/{repo.name}" if repo else "this repository"
            arch_summary_raw = repo.architecture_summary if repo else "{}"
            try:
                arch_summary = json.loads(arch_summary_raw, strict=False)
            except Exception:
                arch_summary = {}

        # 2. Build explanation persona
        personas = {
            "beginner": "Explain using simple analogies and conceptual overviews. Avoid deep syntactical syntax unless asked. Focus on 'why' and 'what'.",
            "intermediate": "Explain focusing on specific files, directory structures, and code architecture. Use typical developer terms (e.g. interfaces, REST API, state management).",
            "expert": "Explain detailing code syntax, dependency resolution, execution timelines, performance bottlenecks, caching patterns, concurrency levels, and system design patterns."
        }
        persona = personas.get(mode, personas["intermediate"])

        # 3. Format Context
        chunks_str = ""
        for item in context.get("chunks", []):
            chunks_str += f"--- Code Symbol: {item['symbol_name']} in {item['file_path']} ---\n"
            chunks_str += f"{item['content']}\n\n"
            
        neighbors_str = ""
        for item in context.get("files_context", []):
            neighbors_str += f"--- Neighbor File Context: {item['file_path']} ---\n"
            neighbors_str += f"{item['content']}\n\n"

        system_prompt = f"""
You are an expert, world-class AI Software Architect named Antigravity.
Your job is to explain the code, APIs, database, and architecture of {repo_title} based on the retrieved code chunks, file structure, and dependency graph neighbors.

Your Target Audience Level: {mode.upper()}
Explanation Guideline: {persona}

Repository Summary:
{json.dumps(arch_summary.get('purpose', ''))}
Tech Stack:
{json.dumps(arch_summary.get('tech_stack', ''))}

=== RELEVANT CODE SYMBOLS ===
{chunks_str}

=== DEPENDENCY GRAPH NEIGHBORS ===
{neighbors_str}

Instruction:
1. Ground your answer in the provided code snippets.
2. If you don't know the answer, state that you cannot find the relevant code in the indexed parts of the repo. Do not hallucinate.
3. Keep the code style clear, utilizing markdown headers and blockquotes where useful.
"""
        # Format chat history
        messages = [{"role": "system", "content": system_prompt}]
        for chat in history[-6:]:  # include last 3 exchanges (6 messages)
            messages.append({"role": chat["role"], "content": chat["content"]})
            
        messages.append({"role": "user", "content": query})
        
        # Call Groq API (we store answer, but frontend will call stream directly for interactive streaming UI)
        answer = await self.groq_client.get_chat_response(messages)
        
        return {
            "answer": answer
        }

    # ----------------------------------------------------
    # BUILD AND COMPILE GRAPHS
    # ----------------------------------------------------
    def get_ingestion_flow(self) -> StateGraph:
        builder = StateGraph(IngestionState)
        
        # Add Nodes
        builder.add_node("fetch_tree", self.fetch_tree_node)
        builder.add_node("prioritize", self.prioritize_node)
        builder.add_node("fetch_contents", self.fetch_contents_node)
        builder.add_node("parse_ast", self.parse_ast_node)
        builder.add_node("generate_graph", self.generate_graph_node)
        builder.add_node("summarize_repo", self.summarize_repo_node)
        builder.add_node("vector_store", self.vector_store_node)
        
        # Set Entrypoint
        builder.set_entry_point("fetch_tree")
        
        # Add Transitions
        builder.add_edge("fetch_tree", "prioritize")
        builder.add_edge("prioritize", "fetch_contents")
        builder.add_edge("fetch_contents", "parse_ast")
        builder.add_edge("parse_ast", "generate_graph")
        builder.add_edge("generate_graph", "summarize_repo")
        builder.add_edge("summarize_repo", "vector_store")
        builder.add_edge("vector_store", END)
        
        return builder.compile()

    def get_chat_flow(self) -> StateGraph:
        builder = StateGraph(ChatState)
        
        builder.add_node("retrieve", self.retrieve_node)
        builder.add_node("reasoning", self.reasoning_node)
        
        builder.set_entry_point("retrieve")
        builder.add_edge("retrieve", "reasoning")
        builder.add_edge("reasoning", END)
        
        return builder.compile()
