import logging
import requests
import json
from typing import list, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Feilds
from sqlalchemy.orm import Session
from app.database.session import get_db, init_db
from app.config.settings import settings
from app.utils.utils import setup_logging
from fastapi import FastAPI

app = FastAPI(title="Repository RAG")

@app.get("/")
def health_check():
    return {"status": "running"}
