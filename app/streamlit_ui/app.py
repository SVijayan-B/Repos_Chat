import streamlit as st
import requests
import json
from typing import Dict, Any, List

# Configure page settings
st.set_page_config(
    page_title="Antigravity — Repository Intelligence Chatbot",
    page_icon="✨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium Gemini-themed CSS
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;700&display=swap');

    /* Main App Background & Colors */
    .stApp {
        background-color: #080a10;
        color: #e2e8f0;
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }
    
    /* Headers & Fonts */
    h1, h2, h3, h4 {
        font-family: 'Outfit', sans-serif !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em;
    }
    
    /* Glowing main Gemini title */
    .gemini-title-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        margin-top: 1.5rem;
        margin-bottom: 2.5rem;
    }
    
    .gemini-title {
        background: linear-gradient(135deg, #a5b4fc 0%, #6366f1 25%, #a855f7 50%, #ec4899 75%, #f43f5e 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5rem;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0.25rem;
        letter-spacing: -0.03em;
        filter: drop-shadow(0 2px 8px rgba(99, 102, 241, 0.25));
    }
    
    .gemini-subtitle {
        text-align: center;
        color: #94a3b8;
        font-size: 1.15rem;
        font-weight: 300;
        max-width: 600px;
        line-height: 1.6;
    }

    /* Glassmorphic Suggestion Cards */
    .suggestion-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 1rem;
        margin-bottom: 2rem;
    }
    
    .suggestion-card {
        background: rgba(30, 41, 59, 0.25);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.25rem;
        cursor: pointer;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        backdrop-filter: blur(12px);
    }
    
    .suggestion-card:hover {
        background: rgba(99, 102, 241, 0.08);
        border: 1px solid rgba(99, 102, 241, 0.25);
        transform: translateY(-4px);
        box-shadow: 0 10px 20px -10px rgba(99, 102, 241, 0.2);
    }
    
    .suggestion-icon {
        font-size: 1.5rem;
        margin-bottom: 0.5rem;
    }
    
    .suggestion-title {
        font-weight: 600;
        color: #ffffff;
        font-size: 0.95rem;
        margin-bottom: 0.25rem;
    }
    
    .suggestion-desc {
        color: #64748b;
        font-size: 0.8rem;
        line-height: 1.4;
    }

    /* Custom Chat Panels */
    .chat-bubble {
        padding: 1.25rem 1.5rem;
        border-radius: 20px;
        margin-bottom: 1.25rem;
        line-height: 1.6;
        font-size: 0.975rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    
    .chat-user {
        background: rgba(99, 102, 241, 0.15);
        color: #e0e7ff;
        margin-left: 20%;
        border-bottom-right-radius: 4px;
        border: 1px solid rgba(99, 102, 241, 0.25);
    }
    
    .chat-assistant {
        background: rgba(30, 41, 59, 0.3);
        color: #f1f5f9;
        margin-right: 20%;
        border-bottom-left-radius: 4px;
        border: 1px solid rgba(255, 255, 255, 0.06);
        position: relative;
    }
    
    .chat-assistant::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, #6366f1, #a855f7, #ec4899);
        border-top-left-radius: 4px;
        border-top-right-radius: 20px;
    }
    
    .chat-header {
        font-family: 'Outfit', sans-serif;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-bottom: 0.5rem;
        letter-spacing: 0.06em;
    }
    
    .user-header {
        color: #818cf8;
    }
    
    .assistant-header {
        background: linear-gradient(90deg, #a5b4fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    /* Interactive Cards */
    .glass-card {
        background: rgba(15, 23, 42, 0.4);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 1.25rem;
        backdrop-filter: blur(16px);
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.2);
    }
</style>
""", unsafe_allow_html=True)

API_BASE_URL = "http://localhost:8000"

# Initialize Session States
if "repo_id" not in st.session_state:
    st.session_state.repo_id = None
if "repo_name" not in st.session_state:
    st.session_state.repo_name = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "arch_summary" not in st.session_state:
    st.session_state.arch_summary = {}
if "selected_suggestion" not in st.session_state:
    st.session_state.selected_suggestion = None

# Sidebar settings
with st.sidebar:
    st.markdown("### 🌌 Ingest Repository")
    st.markdown("Supply any GitHub Repository URL to start the deep code exploration.")
    
    github_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/owner/repo",
        help="Paste a public github repository URL"
    )
    
    branch_override = st.text_input(
        "Branch (Optional)",
        placeholder="e.g. main",
        help="Defaults to primary branch if left empty."
    )
    
    ingest_btn = st.button("🚀 Ingest & Index", use_container_width=True)
    
    st.divider()
    
    st.markdown("### 🧠 Explanation Level")
    # Default is set to 'beginner' (index 0) for highly detailed code breakdowns and analogies!
    explanation_mode = st.radio(
        "Explain output as:",
        options=["beginner", "intermediate", "expert"],
        format_func=lambda x: x.capitalize(),
        index=0,
        help="Beginner: Analogies, concepts and clean algorithm tracing; Intermediate: Core directory & logic; Expert: Detailed syntax & bottlenecks."
    )
    
    st.divider()
    
    if st.session_state.repo_id:
        st.success(f"Active Codebase: **{st.session_state.repo_name}**")
        if st.button("🧹 Reset Chat History", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.selected_suggestion = None
            st.rerun()

# Processing Ingestion Request
if ingest_btn and github_url:
    with st.spinner("Analyzing repository structures, computing syntax AST, building dependency graph..."):
        try:
            res = requests.post(
                f"{API_BASE_URL}/ingest",
                json={"url": github_url, "branch": branch_override or None},
                timeout=120
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.repo_id = data["repository_id"]
                st.session_state.repo_name = f"{data['owner']}/{data['repo']}"
                st.session_state.arch_summary = data.get("architecture_summary", {})
                st.session_state.chat_history = []  # Reset chat on new repo ingest
                st.toast(f"Successfully indexed {st.session_state.repo_name}!", icon="✨")
            else:
                error_detail = res.json().get("detail", "Unknown backend error.")
                st.error(f"Ingestion Failed: {error_detail}")
        except Exception as e:
            st.error(f"Failed to connect to backend server: {e}")

# Header Title
st.markdown("""
<div class="gemini-title-container">
    <div class="gemini-title">Antigravity</div>
    <div class="gemini-subtitle">Interactive AI Software Architect specialized in explaining code, logical terms, database relations, and computational structures of git repositories.</div>
</div>
""", unsafe_allow_html=True)

# Main Application Layout
if not st.session_state.repo_id:
    # Landing Page State
    st.markdown("<div class='glass-card' style='text-align: center;'>", unsafe_allow_html=True)
    st.subheader("Initialize the Chatbot")
    st.markdown("""
    To begin, enter a public GitHub repository link in the left sidebar and click **Ingest & Index**.
    
    The AI system will parse the repository tree, build a NetworkX knowledge graph, parse class/function ASTs, and prepare a custom chatbot tailored to answer all your code queries natively.
    """)
    st.markdown("</div>", unsafe_allow_html=True)
else:
    # Tab navigation matching professional dashboard
    tab1, tab2, tab3 = st.tabs(["✨ Codebase Chatbot", "📋 Architectural Dossier", "🌐 Module Import Graph"])
    
    # ----------------------------------------------------
    # TAB 1: CODEBASE CHATBOT (Gemini Themed)
    # ----------------------------------------------------
    with tab1:
        st.markdown(f"### Exploring Codebases: **{st.session_state.repo_name}**")
        
        # Display existing message history
        for msg in st.session_state.chat_history:
            role_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
            role_header = "Developer" if msg["role"] == "user" else "Antigravity Assistant"
            header_class = "user-header" if msg["role"] == "user" else "assistant-header"
            st.markdown(f"""
            <div class="chat-bubble {role_class}">
                <div class="chat-header {header_class}">{role_header}</div>
                {msg['content']}
            </div>
            """, unsafe_allow_html=True)
            
        # Suggested prompt buttons for smooth workflow (Gemini suggestions)
        st.markdown("<p style='font-size: 0.85rem; color: #64748b; font-weight: 600; margin-bottom: 0.5rem;'>SUGGESTED EXPLORATIONS</p>", unsafe_allow_html=True)
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            if st.button("🔍 Explain Repository Purpose", use_container_width=True):
                st.session_state.selected_suggestion = "Explain this repository and its main goals."
        with col_s2:
            if st.button("🚀 Trace Request flow & APIs", use_container_width=True):
                st.session_state.selected_suggestion = "Explain how the APIs are structured and trace the execution path of a request."
        with col_s3:
            if st.button("💾 Trace Database Interactions", use_container_width=True):
                st.session_state.selected_suggestion = "Explain the database schema, tables, models, and how queries are handled."
        with col_s4:
            if st.button("🧩 Explain Core Logics & Algorithms", use_container_width=True):
                st.session_state.selected_suggestion = "Break down the core logic, functions, and key algorithms used inside this codebase."

        # Input box
        prompt = st.chat_input("Ask about the computational structures, specific code blocks, or import dependency flows...")
        
        # Override prompt if a suggestion was clicked
        if st.session_state.selected_suggestion:
            prompt = st.session_state.selected_suggestion
            st.session_state.selected_suggestion = None  # Reset
            
        if prompt:
            # Render user message
            st.markdown(f"""
            <div class="chat-bubble chat-user">
                <div class="chat-header user-header">Developer</div>
                {prompt}
            </div>
            """, unsafe_allow_html=True)
            
            # Save user message to history
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            
            # Call backend /chat with streaming
            try:
                payload = {
                    "repo_id": st.session_state.repo_id,
                    "query": prompt,
                    "explanation_mode": explanation_mode,
                    "chat_history": st.session_state.chat_history[:-1]
                }
                
                # Setup streaming placeholder
                placeholder = st.empty()
                stream_buffer = ""
                
                # Fetch stream response
                with requests.post(f"{API_BASE_URL}/chat", json=payload, stream=True) as r:
                    if r.status_code == 200:
                        for chunk in r.iter_content(chunk_size=None, decode_unicode=True):
                            if chunk:
                                stream_buffer += chunk
                                placeholder.markdown(f"""
                                <div class="chat-bubble chat-assistant">
                                    <div class="chat-header assistant-header">Antigravity Assistant ({explanation_mode.upper()} mode)</div>
                                    {stream_buffer}
                                </div>
                                """, unsafe_allow_html=True)
                        
                        # Add complete assistant message to history
                        st.session_state.chat_history.append({"role": "assistant", "content": stream_buffer})
                        st.rerun()
                    else:
                        st.error(f"Chat failed with status code: {r.status_code}")
            except Exception as e:
                st.error(f"Failed to connect or fetch streaming chat: {e}")

    # ----------------------------------------------------
    # TAB 2: ARCHITECTURAL DOSSIER
    # ----------------------------------------------------
    with tab2:
        st.subheader("📋 Core Project Architecture Dossier")
        summary = st.session_state.arch_summary
        
        if not summary:
            st.info("No architectural dossier generated for this repository.")
        else:
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.markdown("#### 🌟 Project Purpose")
                st.markdown(f"<div class='glass-card'>{summary.get('purpose', 'N/A')}</div>", unsafe_allow_html=True)
                
                st.markdown("#### 🛠️ Tech Stack & Dependencies")
                st.markdown(f"<div class='glass-card'>{summary.get('tech_stack', 'N/A')}</div>", unsafe_allow_html=True)
                
                st.markdown("#### 🏗️ Architecture Design Patterns")
                st.markdown(f"<div class='glass-card'>{summary.get('architecture_overview', 'N/A')}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("#### ⚙️ Execution Flow & Initialization")
                st.markdown(f"<div class='glass-card'>{summary.get('execution_flow', 'N/A')}</div>", unsafe_allow_html=True)
                
                st.markdown("#### 🔌 API Routes & Routing Patterns")
                st.markdown(f"<div class='glass-card'>{summary.get('api_structure', 'N/A')}</div>", unsafe_allow_html=True)
                
                st.markdown("#### 💾 Database Models & Storage")
                st.markdown(f"<div class='glass-card'>{summary.get('database_structure', 'N/A')}</div>", unsafe_allow_html=True)

    # ----------------------------------------------------
    # TAB 3: MODULE IMPORT GRAPH
    # ----------------------------------------------------
    with tab3:
        st.subheader("🌐 Interactive Module Dependency Mappings")
        st.markdown("Visual diagram showcasing import connections between file modules across the codebase repository.")
        
        try:
            res = requests.get(f"{API_BASE_URL}/repo/{st.session_state.repo_id}/graph")
            if res.status_code == 200:
                graph_data = res.json()
                
                if not graph_data.get("edges"):
                    st.info("No module-level import edges detected. This may be a single-file project or uses dynamic imports.")
                else:
                    dot_parts = [
                        "digraph G {",
                        "  bgcolor=\"transparent\";",
                        "  node [style=filled, fillcolor=\"#1e293b\", color=\"#475569\", fontcolor=\"#ffffff\", fontname=\"Helvetica\", shape=box, style=\"rounded,filled\"];",
                        "  edge [color=\"#818cf8\", arrowhead=vee];"
                    ]
                    
                    for node in graph_data["nodes"]:
                        dot_parts.append(f'  "{node["id"]}" [label="{node["label"]}"];')
                        
                    for edge in graph_data["edges"]:
                        dot_parts.append(f'  "{edge["source"]}" -> "{edge["target"]}";')
                        
                    dot_parts.append("}")
                    dot_str = "\n".join(dot_parts)
                    
                    st.graphviz_chart(dot_str, use_container_width=True)
            else:
                st.error("Failed to retrieve codebase relationship graph.")
        except Exception as e:
            st.error(f"Error fetching/rendering graph: {e}")
