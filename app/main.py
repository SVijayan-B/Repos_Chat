import logging
import requests
import json
from typing import list, Dict, Any, Optional
from pydantic import BaseModel, Feilds
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.utils.utils import setup_logging
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from sqlalchemy import select
from app.database.session import get_db, init_db, SessionLocal
from app.models.db_models import Repository
from app.workflows.orchestrator import WorkflowOrchestrator

app = FastAPI(title="Antigravity RAG System Engine Core Pipeline Platform Manager Spec")
orchestrator = WorkflowOrchestrator()

@app.on_event("startup")
async def on_startup():
    await init_db()

class IngestReq(BaseModel): url: str

async def run_ingest(owner: str, repo: str):
    flow = orchestrator.get_ingestion_flow()
    await flow.ainvoke({"owner": owner, "repo": repo, "branch": "main", "tree": [], "prioritized_files": [], "fetched_files": [], "chunks": [], "architecture_summary": {}, "progress": "", "repo_id": None})

@app.post("/repo/ingest")
async def ingest(payload: IngestReq, bg: BackgroundTasks):
    parts = payload.url.replace("https://github.com/", "").strip("/").split("/")
    if len(parts) < 2: raise HTTPException(status_code=400, detail="Invalid target structural path link URL mapping layout format.")
    bg.add_task(run_ingest, parts[0], parts[1])
    return {"status": "queued", "message": "Asynchronous background background processing worker pipeline loops activated successfully!"}

@app.get("/repo/active")
async def active_repos():
    async with SessionLocal() as db:
        res = await db.execute(select(Repository))
        repos = res.scalars().all()
        return [{"id": r.id, "owner": r.owner, "repo": r.name} for r in repos]