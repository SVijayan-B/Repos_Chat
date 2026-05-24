import logging
import re
import json
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.logging import setup_logging
from app.config.settings import settings
from app.database.session import init_db, get_db, SessionLocal
from app.models.db_models import Repository, GraphEdge
from app.workflows.orchestrator import WorkflowOrchestrator, ChatState, IngestionState

# Setup Logging
setup_logging()
logger = logging.getLogger(__name__)

# FastAPI initialization
app = FastAPI(
    title="AI Repository Intelligence System",
    description="Intelligent repository-aware RAG for public GitHub repos without cloning.",
    version="1.0.0"
)

# Initialize workflow orchestrator singleton
orchestrator = WorkflowOrchestrator()

@app.on_event("startup")
async def startup_event():
    """Run database initialization on application startup."""
    logger.info("Starting up FastAPI application...")
    await init_db()

# Pydantic Schemas
class IngestRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL (e.g. https://github.com/owner/repo or https://github.com/owner/repo/tree/branch)")
    branch: Optional[str] = Field(None, description="Optional branch override. If not specified, parsed from URL or fetched from GitHub default branch.")

class ChatMessage(BaseModel):
    role: str  # user or assistant
    content: str

class ChatRequest(BaseModel):
    repo_id: int = Field(..., description="ID of the ingested repository in PostgreSQL")
    query: str = Field(..., description="Developer question")
    explanation_mode: str = Field("intermediate", description="Explanation detail level: beginner, intermediate, expert")
    chat_history: List[ChatMessage] = Field(default_factory=list, description="Recent conversation history")

# Utilities
def parse_github_url(url: str) -> tuple[str, str, Optional[str]]:
    """
    Extracts owner, repo, and branch from a GitHub URL.
    Handles:
      https://github.com/owner/repo
      https://github.com/owner/repo/tree/branch-name
      https://github.com/owner/repo/tree/feature/some-branch
    """
    url_clean = url.strip().rstrip("/")
    # Pattern to match: github.com/<owner>/<repo>
    m = re.search(r"github\.com/([^/]+)/([^/]+)", url_clean)
    if not m:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL format. Must point to a repository on github.com.")
    
    owner = m.group(1)
    repo = m.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    
    # Check if a branch is specified in the URL path (e.g., /tree/<branch>)
    branch = None
    tree_marker = f"github.com/{owner}/{repo}/tree/"
    if tree_marker in url_clean:
        parts = url_clean.split(tree_marker)
        if len(parts) > 1:
            branch = parts[1]
            
    return owner, repo, branch

# Endpoints
@app.get("/health")
async def health_check():
    """Verify application health and availability."""
    return {
        "status": "healthy",
        "settings": {
            "embedding_model": settings.embedding_model,
            "groq_model": settings.groq_model,
            "concurrency_limit": settings.concurrency_limit
        }
    }

@app.post("/ingest")
async def ingest_repository(req: IngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Asynchronously ingests a GitHub repository.
    Fetches structures, parses AST, runs graph resolution, generates summaries,
    generates embeddings, and stores in PostgreSQL.
    """
    owner, repo, url_branch = parse_github_url(req.url)
    
    # Determine branch to use:
    # 1. Override in request
    # 2. Parsed from tree URL
    # 3. Fetch default branch from GitHub metadata
    branch = req.branch or url_branch
    if not branch:
        # Fallback to fetching default branch from GitHub API
        logger.info(f"Querying default branch metadata for {owner}/{repo}")
        async with aiohttp_client_session() as session:
            url = f"https://api.github.com/repos/{owner}/{repo}"
            headers = {"Accept": "application/vnd.github.v3+json"}
            if settings.github_pat:
                headers["Authorization"] = f"Bearer {settings.github_pat}"
            try:
                async with session.get(url, headers=headers, timeout=15) as response:
                    if response.status == 200:
                        meta = await response.json()
                        branch = meta.get("default_branch", "main")
                    else:
                        branch = "main"
            except Exception:
                branch = "main"
                
    logger.info(f"Triggering ingestion workflow for: {owner}/{repo} (branch: {branch})")
    
    # Run the LangGraph ingestion workflow
    ingestion_flow = orchestrator.get_ingestion_flow()
    initial_state = IngestionState(
        owner=owner,
        repo=repo,
        branch=branch,
        repo_id=None,
        tree=[],
        prioritized_files=[],
        fetched_files=[],
        chunks=[],
        architecture_summary={},
        progress="Starting ingestion pipeline."
    )
    
    try:
        final_state = await ingestion_flow.ainvoke(initial_state)
        
        # Fetch the newly created repository record from DB to verify
        repo_id = final_state.get("repo_id")
        if not repo_id:
            raise HTTPException(status_code=500, detail="Ingestion failed. Repository ID was not generated.")
            
        return {
            "success": True,
            "repository_id": repo_id,
            "owner": owner,
            "repo": repo,
            "branch": branch,
            "architecture_summary": final_state.get("architecture_summary"),
            "message": final_state.get("progress")
        }
    except Exception as e:
        logger.exception("Error during repository ingestion workflow execution:")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

@app.post("/chat")
async def chat_repository(req: ChatRequest):
    """
    Query the ingested repository with streaming responses.
    Utilizes local embeddings for semantic retrieval, NetworkX graph for neighbor expansion,
    and Groq client for streamed text response generation.
    """
    logger.info(f"Received chat request for repo_id: {req.repo_id}")
    
    # 1. Convert chat history schema
    history_list = [{"role": msg.role, "content": msg.content} for msg in req.chat_history]
    
    # 2. Run retrieval node directly to get context
    chat_flow = orchestrator.get_chat_flow()
    
    initial_state = ChatState(
        repo_id=req.repo_id,
        query=req.query,
        explanation_mode=req.explanation_mode,
        chat_history=history_list,
        context={},
        answer=""
    )
    
    # Run the retrieval phase
    try:
        retrieval_state = await orchestrator.retrieve_node(initial_state)
        context = retrieval_state.get("context", {})
    except Exception as e:
        logger.error(f"Failed context retrieval during chat: {e}")
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    # 3. Create generator to stream responses from Groq
    async def stream_generator():
        # Retrieve repository details
        async with SessionLocal() as db:
            stmt = select(Repository).where(Repository.id == req.repo_id)
            res = await db.execute(stmt)
            repo = res.scalars().first()
            repo_title = f"{repo.owner}/{repo.name}" if repo else "this repository"
            arch_summary_raw = repo.architecture_summary if repo else "{}"
            try:
                arch_summary = json.loads(arch_summary_raw, strict=False)
            except Exception:
                arch_summary = {}

        personas = {
            "beginner": "Explain using simple analogies and conceptual overviews. Avoid deep syntactical syntax unless asked. Focus on 'why' and 'what'.",
            "intermediate": "Explain focusing on specific files, directory structures, and code architecture. Use typical developer terms (e.g. interfaces, REST API, state management).",
            "expert": "Explain detailing code syntax, dependency resolution, execution timelines, performance bottlenecks, caching patterns, concurrency levels, and system design patterns."
        }
        persona = personas.get(req.explanation_mode, personas["intermediate"])

        # Format retrieved context
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

Your Target Audience Level: {req.explanation_mode.upper()}
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
        messages = [{"role": "system", "content": system_prompt}]
        for chat in history_list[-6:]:
            messages.append(chat)
        messages.append({"role": "user", "content": req.query})

        async for chunk in orchestrator.groq_client.get_chat_response_stream(messages):
            yield chunk

    return StreamingResponse(stream_generator(), media_type="text/event-stream")

@app.get("/repos")
async def list_repositories(db: AsyncSession = Depends(get_db)):
    """List all ingested repositories."""
    stmt = select(Repository).order_by(Repository.created_at.desc())
    res = await db.execute(stmt)
    repos = res.scalars().all()
    return [
        {
            "id": r.id,
            "owner": r.owner,
            "name": r.name,
            "default_branch": r.default_branch
        } for r in repos
    ]

@app.get("/repo/{repo_id}/summary")
async def get_repository_summary(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch the parsed architecture JSON report of the repository."""
    stmt = select(Repository).where(Repository.id == repo_id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
        
    try:
        summary_data = json.loads(repo.architecture_summary, strict=False)
    except Exception:
        summary_data = {"error": "Failed to parse architecture summary."}
        
    return {
        "repo_id": repo.id,
        "owner": repo.owner,
        "repo": repo.name,
        "branch": repo.default_branch,
        "summary": summary_data
    }

@app.delete("/repo/{repo_id}")
async def delete_repository(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Delete repository and all its cascading files, chunks, and graph edges."""
    stmt = select(Repository).where(Repository.id == repo_id)
    res = await db.execute(stmt)
    repo = res.scalars().first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found.")
    await db.delete(repo)
    await db.commit()
    return {"success": True, "message": "Repository and all cascading assets successfully deleted."}

@app.get("/repo/{repo_id}/graph")
async def get_repository_graph(repo_id: int, db: AsyncSession = Depends(get_db)):
    """Fetch the serialized dependency edges list for visualization."""
    stmt = select(GraphEdge).where(GraphEdge.repository_id == repo_id)
    res = await db.execute(stmt)
    edges = res.scalars().all()
    
    nodes_set = set()
    edges_list = []
    for edge in edges:
        nodes_set.add(edge.source)
        nodes_set.add(edge.target)
        edges_list.append({
            "source": edge.source,
            "target": edge.target,
            "type": edge.type
        })
        
    return {
        "nodes": [{"id": node, "label": node.split("/")[-1]} for node in nodes_set],
        "edges": edges_list
    }

# Helper class for default branch query
import aiohttp
from contextlib import asynccontextmanager

@asynccontextmanager
async def aiohttp_client_session():
    async with aiohttp.ClientSession() as session:
        yield session
