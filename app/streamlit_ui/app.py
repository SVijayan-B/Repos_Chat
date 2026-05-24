import streamlit as st
import requests
import json
from typing import Dict, Any, List

# Configure page settings
st.set_page_config(
    page_title="RepoChat — Codebase Intelligence Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Premium HTML/CSS - Black, Blue, and Green theme
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');

    /* Global resets */
    .stApp {
        background-color: #030407 !important;
        color: #e2e8f0 !important;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif !important;
    }

    /* Headings */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Outfit', sans-serif !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Custom scrollbars */
    ::-webkit-scrollbar {
        width: 6px;
        height: 6px;
    }
    ::-webkit-scrollbar-track {
        background: #030407;
    }
    ::-webkit-scrollbar-thumb {
        background: rgba(16, 185, 129, 0.25);
        border-radius: 99px;
    }
    ::-webkit-scrollbar-thumb:hover {
        background: rgba(16, 185, 129, 0.5);
    }

    /* ChatGPT style Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #07090e !important;
        border-right: 1px solid rgba(16, 185, 129, 0.15) !important;
    }

    /* Glowing Sidebar buttons and lists */
    section[data-testid="stSidebar"] button {
        background-color: rgba(59, 130, 246, 0.08) !important;
        color: #60a5fa !important;
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }
    section[data-testid="stSidebar"] button:hover {
        background-color: #3b82f6 !important;
        color: #ffffff !important;
        border-color: #3b82f6 !important;
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.4) !important;
    }

    /* New Chat Button */
    .new-chat-btn button {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(59, 130, 246, 0.15)) !important;
        color: #34d399 !important;
        border: 1px solid rgba(16, 185, 129, 0.3) !important;
        font-weight: 600 !important;
    }
    .new-chat-btn button:hover {
        background: linear-gradient(135deg, #10b981, #3b82f6) !important;
        color: #ffffff !important;
        border-color: #10b981 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.4) !important;
    }

    /* Main Header container */
    .repochat-header-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 3rem 1rem 1.5rem 1rem;
        background: radial-gradient(circle at top, rgba(16, 185, 129, 0.1) 0%, transparent 60%);
        border-radius: 24px;
        margin-bottom: 1.5rem;
    }

    .repochat-title {
        background: linear-gradient(135deg, #34d399 0%, #10b981 40%, #3b82f6 70%, #60a5fa 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-family: 'Outfit', sans-serif;
        font-size: 4.5rem;
        font-weight: 800;
        text-align: center;
        letter-spacing: -0.04em;
        margin-bottom: 0.5rem;
        filter: drop-shadow(0 4px 15px rgba(16, 185, 129, 0.25));
    }

    .repochat-subtitle {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-weight: 300;
        font-size: 1.2rem;
        color: #94a3b8;
        text-align: center;
        max-width: 700px;
        line-height: 1.6;
    }

    /* Premium Main Card for url entry */
    .ingest-card {
        background: rgba(10, 15, 26, 0.7);
        border: 1px solid rgba(16, 185, 129, 0.15);
        border-radius: 24px;
        padding: 2.5rem;
        margin: 1rem auto;
        max-width: 800px;
        backdrop-filter: blur(24px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.5), 0 0 40px rgba(16, 185, 129, 0.05);
        transition: border 0.3s ease;
    }
    .ingest-card:hover {
        border-color: rgba(16, 185, 129, 0.3);
    }

    /* Premium chat bubble styling */
    .chat-bubble {
        padding: 1.25rem 1.65rem !important;
        border-radius: 24px !important;
        margin-bottom: 1.25rem !important;
        line-height: 1.65 !important;
        font-size: 0.975rem !important;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2) !important;
        animation: bubblePop 0.4s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    @keyframes bubblePop {
        0% { opacity: 0; transform: translateY(10px) scale(0.98); }
        100% { opacity: 1; transform: translateY(0) scale(1); }
    }

    .chat-user {
        background: rgba(59, 130, 246, 0.12) !important;
        color: #e0e7ff !important;
        margin-left: 15% !important;
        border-bottom-right-radius: 4px !important;
        border: 1px solid rgba(59, 130, 246, 0.25) !important;
    }

    .chat-assistant {
        background: rgba(10, 15, 26, 0.7) !important;
        color: #f1f5f9 !important;
        margin-right: 15% !important;
        border-bottom-left-radius: 4px !important;
        border: 1px solid rgba(16, 185, 129, 0.15) !important;
        position: relative !important;
    }

    /* Emerald green indicator line on assistant answers */
    .chat-assistant::before {
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 3px !important;
        background: linear-gradient(90deg, #10b981, #3b82f6) !important;
        border-top-left-radius: 4px !important;
        border-top-right-radius: 24px !important;
    }

    .chat-header {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.75rem !important;
        text-transform: uppercase !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 0.08em !important;
    }

    .user-header {
        color: #60a5fa !important;
    }

    .assistant-header {
        background: linear-gradient(90deg, #34d399, #60a5fa) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
    }

    /* Active chat highlights */
    .active-chat-highlight {
        background: rgba(16, 185, 129, 0.12) !important;
        border: 1px solid #10b981 !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
        margin-bottom: 0.5rem !important;
        color: #34d399 !important;
        font-weight: 600 !important;
        font-family: 'Outfit', sans-serif !important;
        font-size: 0.9rem !important;
        text-align: left !important;
        box-shadow: 0 0 10px rgba(16, 185, 129, 0.15) !important;
    }

    /* Ingestion Button */
    .ingest-btn button {
        background: linear-gradient(135deg, #10b981 0%, #3b82f6 100%) !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 14px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 1.05rem !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.3s ease !important;
    }
    .ingest-btn button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 24px rgba(16, 185, 129, 0.4) !important;
    }

    .glass-card {
        background: rgba(10, 15, 26, 0.45) !important;
        border: 1px solid rgba(255, 255, 255, 0.04) !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        margin-bottom: 1.25rem !important;
        backdrop-filter: blur(16px) !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3) !important;
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
if "repos_list" not in st.session_state:
    st.session_state.repos_list = []
if "explanation_mode" not in st.session_state:
    st.session_state.explanation_mode = "beginner"

# Fetch active repositories from backend list endpoint
try:
    repos_res = requests.get(f"{API_BASE_URL}/repos", timeout=10)
    if repos_res.status_code == 200:
        st.session_state.repos_list = repos_res.json()
except Exception:
    st.session_state.repos_list = []

# Render ChatGPT-style Sidebar for Chat History
with st.sidebar:
    st.markdown("<h2 style='font-size: 1.35rem; margin-top: 1rem; margin-bottom: 1.5rem; font-family: Outfit; font-weight: 700;'>🤖 RepoChat</h2>", unsafe_allow_html=True)
    
    # Large "+ New Chat" Button
    st.markdown('<div class="new-chat-btn">', unsafe_allow_html=True)
    new_chat_clicked = st.button("➕ New Chat / Ingest", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    if new_chat_clicked:
        st.session_state.repo_id = None
        st.session_state.repo_name = ""
        st.session_state.chat_history = []
        st.session_state.arch_summary = {}
        st.session_state.selected_suggestion = None
        st.rerun()
        
    st.markdown("<p style='font-size: 0.7rem; color: #64748b; font-weight: 700; margin-top: 2rem; margin-bottom: 0.75rem; letter-spacing: 0.06em;'>ACTIVE CODBASES</p>", unsafe_allow_html=True)
    
    # Render previously ingested repositories as chats
    if not st.session_state.repos_list:
        st.markdown("<p style='font-size: 0.8rem; color: #475569; font-style: italic;'>No ingested repos yet.</p>", unsafe_allow_html=True)
    else:
        for r in st.session_state.repos_list:
            col_btn, col_del = st.columns([8, 2])
            label = f"📁 {r['owner']}/{r['name']}"
            
            with col_btn:
                # If current active codebase matches, highlight it
                if st.session_state.repo_id == r['id']:
                    st.markdown(f'<div class="active-chat-highlight">{label}</div>', unsafe_allow_html=True)
                else:
                    # Clicking a repository shifts context
                    if st.button(label, key=f"hist_repo_{r['id']}", use_container_width=True):
                        st.session_state.repo_id = r['id']
                        st.session_state.repo_name = f"{r['owner']}/{r['name']}"
                        st.session_state.chat_history = []
                        st.session_state.selected_suggestion = None
                        # Load summary
                        try:
                            summary_res = requests.get(f"{API_BASE_URL}/repo/{r['id']}/summary")
                            if summary_res.status_code == 200:
                                st.session_state.arch_summary = summary_res.json().get("summary", {})
                        except Exception:
                            st.session_state.arch_summary = {}
                        st.rerun()
            with col_del:
                if st.button("🗑️", key=f"del_repo_{r['id']}", help="Delete this chat and all corresponding data"):
                    try:
                        del_res = requests.delete(f"{API_BASE_URL}/repo/{r['id']}")
                        if del_res.status_code == 200:
                            st.toast(f"Deleted successfully!", icon="🗑️")
                            # If active repo was deleted, clear active state
                            if st.session_state.repo_id == r['id']:
                                st.session_state.repo_id = None
                                st.session_state.repo_name = ""
                                st.session_state.chat_history = []
                                st.session_state.arch_summary = {}
                            st.rerun()
                        else:
                            st.error("Failed to delete codebase.")
                    except Exception as e:
                        st.error(f"Error: {e}")

# Processing Ingestion Request
def handle_ingestion(url: str, branch: str, mode: str):
    if not url:
        st.error("Please provide a valid GitHub repository URL!")
        return
        
    with st.spinner("Analyzing codebase AST, resolving dependencies, generating embeddings..."):
        try:
            res = requests.post(
                f"{API_BASE_URL}/ingest",
                json={"url": url, "branch": branch or None},
                timeout=120
            )
            if res.status_code == 200:
                data = res.json()
                st.session_state.repo_id = data["repository_id"]
                st.session_state.repo_name = f"{data['owner']}/{data['repo']}"
                st.session_state.arch_summary = data.get("architecture_summary", {})
                st.session_state.chat_history = []
                st.session_state.explanation_mode = mode
                st.toast(f"Successfully connected to {st.session_state.repo_name}!", icon="✨")
                st.rerun()
            else:
                error_detail = res.json().get("detail", "Unknown backend error.")
                st.error(f"Ingestion Failed: {error_detail}")
        except Exception as e:
            st.error(f"Failed to connect to backend server: {e}")

# Render Header Title
st.markdown("""
<div class="repochat-header-container">
    <div class="repochat-title">RepoChat</div>
    <div class="repochat-subtitle">A premium, ChatGPT-structured Repository Intelligence Chatbot designed to trace computational logic, explain code syntax, and map system workflows.</div>
</div>
""", unsafe_allow_html=True)

# Main Application Portal
if not st.session_state.repo_id:
    # ----------------------------------------------------
    # LANDING PORTAL (Ingest in the Main Page)
    # ----------------------------------------------------
    st.markdown('<div class="ingest-card">', unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; margin-bottom: 1.5rem; font-family: Outfit; font-weight: 700;'>🚀 Ingest New Codebase</h3>", unsafe_allow_html=True)
    
    main_url = st.text_input(
        "GitHub Repository Link",
        placeholder="https://github.com/owner/repo",
        help="Paste a public github repository URL directly"
    )
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        main_branch = st.text_input(
            "Branch Override (Optional)",
            placeholder="e.g. main",
            help="Defaults to default branch if left empty."
        )
    with col_c2:
        main_mode = st.selectbox(
            "Explain codebase output as:",
            options=["beginner", "intermediate", "expert"],
            format_func=lambda x: x.capitalize(),
            index=["beginner", "intermediate", "expert"].index(st.session_state.explanation_mode),
            help="Beginner: Concept analogies and detailed logic tracing; Intermediate: File module outline; Expert: Detailed syntax & bottlenecks."
        )
        
    st.markdown("<div style='margin-top: 1.5rem;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="ingest-btn" style="text-align: center;">', unsafe_allow_html=True)
    start_ingest = st.button("🚀 Ingest & Start Chat")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if start_ingest:
        handle_ingestion(main_url, main_branch, main_mode)
        
else:
    # ----------------------------------------------------
    # ACTIVE REPO PORTAL (Tabs for Chat, Architecture, Graph)
    # ----------------------------------------------------
    tab1, tab2, tab3 = st.tabs(["💬 RepoChat Companion", "📋 Architectural Dossier", "🌐 Module Import Graph"])
    
    # TAB 1: CHATBOT INTERFACE
    with tab1:
        col_title, col_mode = st.columns([7, 3])
        with col_title:
            st.markdown(f"### Chat Session: **{st.session_state.repo_name}**")
        with col_mode:
            selected_mode = st.selectbox(
                "Explanation Mode Override",
                options=["beginner", "intermediate", "expert"],
                format_func=lambda x: f"{x.capitalize()} mode",
                index=["beginner", "intermediate", "expert"].index(st.session_state.explanation_mode),
                key="chat_explanation_mode"
            )
            if selected_mode != st.session_state.explanation_mode:
                st.session_state.explanation_mode = selected_mode
                st.rerun()
        
        # Display existing message history
        for msg in st.session_state.chat_history:
            role_class = "chat-user" if msg["role"] == "user" else "chat-assistant"
            role_header = "Developer" if msg["role"] == "user" else "RepoChat Companion"
            header_class = "user-header" if msg["role"] == "user" else "assistant-header"
            st.markdown(f"""
            <div class="chat-bubble {role_class}">
                <div class="chat-header {header_class}">{role_header}</div>
                {msg['content']}
            </div>
            """, unsafe_allow_html=True)
            
        # Suggested prompt buttons for smooth workflow
        st.markdown("<p style='font-size: 0.8rem; color: #4b5563; font-weight: 600; margin-bottom: 0.5rem; letter-spacing: 0.05em;'>SUGGESTED DISCUSSIONS</p>", unsafe_allow_html=True)
        col_s1, col_s2, col_s3, col_s4 = st.columns(4)
        
        with col_s1:
            if st.button("🔍 Explain Repo Purpose", use_container_width=True):
                st.session_state.selected_suggestion = "Explain this repository and its main goals."
        with col_s2:
            if st.button("🚀 Trace API & Requests", use_container_width=True):
                st.session_state.selected_suggestion = "Explain how the APIs are structured and trace the execution path of a request."
        with col_s3:
            if st.button("💾 Trace Database Schema", use_container_width=True):
                st.session_state.selected_suggestion = "Explain the database schema, tables, models, and how queries are handled."
        with col_s4:
            if st.button("🧩 Trace Logical Flow", use_container_width=True):
                st.session_state.selected_suggestion = "Break down the core logic, functions, and key algorithms used inside this codebase."

        # Input box
        prompt = st.chat_input("Ask about specific variables, algorithms, functions, or execution flows...")
        
        # Override prompt if suggestion clicked
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
                    "explanation_mode": st.session_state.explanation_mode,
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
                                    <div class="chat-header assistant-header">RepoChat Companion ({st.session_state.explanation_mode.upper()} mode)</div>
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

    # TAB 2: ARCHITECTURAL DOSSIER
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

    # TAB 3: MODULE IMPORT GRAPH
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
                        "  node [style=filled, fillcolor=\"#0a0f1a\", color=\"#10b981\", fontcolor=\"#ffffff\", fontname=\"Helvetica\", shape=box, style=\"rounded,filled\"];",
                        "  edge [color=\"#3b82f6\", arrowhead=vee];"
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
