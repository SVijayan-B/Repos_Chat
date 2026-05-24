from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from app.database.session import Base

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    owner = Column(String, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    default_branch = Column(String, default="main")
    architecture_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    files = relationship("File", back_populates="repository", cascade="all, delete-orphan")
    edges = relationship("GraphEdge", back_populates="repository", cascade="all, delete-orphan")

class File(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    path = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    priority = Column(String, default="High")  # High, Low, Ignore
    language = Column(String, nullable=True)
    hash = Column(String, nullable=True)

    repository = relationship("Repository", back_populates="files")
    chunks = relationship("Chunk", back_populates="file", cascade="all, delete-orphan")

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path = Column(String, nullable=False)
    symbol_name = Column(String, nullable=True)
    language = Column(String, nullable=True)
    imports = Column(JSON, default=list)  # list of imports
    dependencies = Column(JSON, default=list)  # list of internal symbols referenced
    content = Column(Text, nullable=False)
    summary = Column(Text, nullable=True)
    
    # 384 dimensions matching sentence-transformers/all-MiniLM-L6-v2
    embedding = Column(JSON, nullable=True)

    file = relationship("File", back_populates="chunks")

class GraphEdge(Base):
    __tablename__ = "graph_edges"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String, nullable=False)  # source file path
    target = Column(String, nullable=False)  # target file path
    type = Column(String, default="import")  # import, call, etc.

    repository = relationship("Repository", back_populates="edges")
