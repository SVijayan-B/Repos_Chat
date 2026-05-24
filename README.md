# RepoChat - Advanced Repository-Aware AI Intelligence System

RepoChat is a specialized codebase intelligence platform that enables developers to analyze, query, and trace public GitHub repositories without requiring local cloning. By parsing abstract syntax trees (AST), resolving import dependency graphs, and performing semantic search on local vector embeddings, RepoChat delivers context-aware explanations tailored to different expertise levels.

---

## Core Capabilities

### Centralized Ingestion and Analysis
Users can paste any public GitHub repository link directly into the primary dashboard to initiate an asynchronous analysis pipeline. The system maps the codebase, builds syntax trees, and registers modules on the fly.

### Dynamic Explanation Levels
RepoChat accommodates various developer personas with three customizable levels of query detail, toggleable mid-conversation:
* **Beginner Mode**: Emphasizes conceptual overviews, high-level structural flows, and intuitive analogies rather than syntactical complexities.
* **Intermediate Mode**: Focuses on directory architecture, REST API route maps, and standard programming patterns.
* **Expert Mode**: Traces performance bottlenecks, database caching patterns, execution timelines, and specific file syntax.

### Interactive Module Dependency Graphs
A visual Graphviz dependency map is constructed automatically for each repository. It outlines import connections across modules to assist developers in understanding codebase architecture and dependency pathways.

### Cascading Session Cleanup
To maintain database integrity and optimize storage, RepoChat supports absolute cleanup capabilities. Deleting a chat session from the historical index initiates a recursive deletion cascade across the relational database. This purges the repository record and all associated files, parsed AST chunks, embeddings, and import edges.

---

## Technical Architecture

The system is split into a modular backend service and an interactive web interface:

### Backend Services (FastAPI and LangGraph)
* **AST Parser**: Employs Tree-sitter AST parsing to extract symbols, classes, functions, and import declarations.
* **Graph Builder**: Leverages NetworkX to model and traverse file relationships.
* **Local Embedding Engine**: Uses SentenceTransformers to calculate semantic vectors for index chunks locally. The backend utilizes the pgvector extension for robust vector storage and operations, falling back gracefully to optimized NumPy-based cosine similarity computations in-memory for environments without precompiled local vector binaries.
* **Orchestrator**: Coordinates tasks using LangGraph, executing concurrent ingestion pipelines and hybrid retrieval routines.
* **LLM Core**: Integrates with Groq utilizing Llama 3.3 models to stream natural language developer responses.
* **Data Layer**: Powered by PostgreSQL with pgvector integration and SQLAlchemy AsyncSession, ensuring robust transactional handling, vector capability, and cascading referential integrity.

### Frontend Client (Streamlit and CSS)
* **Glassmorphic UI**: Customized using native HTML5 and modern CSS styling to deliver an Obsidian, Deep Blue, and Emerald Green dark mode interface.
* **Asynchronous Updates**: Renders real-time typing indicators and chunk-based response streams from the backend API.
* **Unified Workspace**: Replaces traditional sidebars with a clean main dashboard card for new codebases, reserving the sidebar strictly for active chat session indexes and cleanup controls.

---

## Technical Stack

### Backend
* Programming Language: Python 3.10+
* Framework: FastAPI, Uvicorn
* ORM and Database: SQLAlchemy (AsyncPG), PostgreSQL with pgvector support
* Graph Representation: NetworkX
* Syntax Analysis: Tree-sitter
* Embeddings: SentenceTransformers (all-MiniLM-L6-v2)
* LLM Provider: Groq API (llama-3.3-70b-versatile)
* Workflow Management: LangGraph

### Frontend
* Interface Builder: Streamlit
* Styling: Vanilla CSS, HTML5
* Client: Requests (HTTP connection handling)

---

## Installation and Setup

### Prerequisites
1. **Python**: Version 3.10 or higher.
2. **PostgreSQL**: An active instance running locally or remotely, with the pgvector extension enabled.
3. **Groq API Key**: A valid token to access Groq inference engines.
4. **GitHub PAT (Optional)**: A personal access token to prevent rate-limiting on public API requests.

### Configuration
Create a `.env` file in the root directory and configure the environment variables:

```env
DATABASE_URL=postgresql+asyncpg://<username>:<password>@localhost:5432/<database_name>
GROQ_API_KEY=your_groq_api_key_here
GITHUB_PAT=your_github_personal_access_token_here
```

### Dependency Installation
1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   * On Windows (Command Prompt / PowerShell):
     ```powershell
     .\venv\Scripts\activate
     ```
   * On macOS / Linux:
     ```bash
     source venv/bin/activate
     ```
3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

---

## Running the Application

To operate RepoChat, two concurrent processes must be started.

### 1. Launch the Backend API
Start the FastAPI service using Uvicorn:
```bash
uvicorn app.main:app --port 8000 --reload
```
The API documentation will be accessible at `http://localhost:8000/docs`.

### 2. Launch the Web Interface
Run the Streamlit web client from another terminal window:
```bash
streamlit run app/streamlit_ui/app.py
```
The user interface will open automatically in your browser at `http://localhost:8501`.
