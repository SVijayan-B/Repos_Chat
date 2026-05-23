import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # GitHub PAT
    github_pat: str = Field(default="", validation_alias="GITHUB_PAT")
    
    # Groq API Key
    groq_api_key: str = Field(default="", validation_alias="GROQ_API_KEY")
    
    # Database Configuration
    database_url: str = Field(
        default="postgresql+asyncpg://postgres@localhost:5432/repo_rag",
        validation_alias="DATABASE_URL"
    )
    
    # Model Configurations
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    groq_model: str = "llama-3.3-70b-versatile"
    
    # Ingestion Controls
    concurrency_limit: int = 10
    max_file_size_kb: int = 500  # Skip very large files to optimize performance
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Instantiate singleton settings
settings = Settings()