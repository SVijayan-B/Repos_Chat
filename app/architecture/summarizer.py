import json
import logging
from typing import Dict, Any, List
from app.llm.groq_client import GroqClient

logger = logging.getLogger(__name__)

class ArchitectureSummarizer:
    def __init__(self, groq_client: GroqClient):
        self.groq_client = groq_client

    async def generate_summary(
        self,
        owner: str,
        repo: str,
        file_tree: List[Dict[str, Any]],
        readme_content: str,
        high_priority_file_summaries: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Synthesizes files, folder structures, and high-level summaries to generate
        a structured architecture overview of the repository.
        """
        logger.info(f"Synthesizing architecture summary for {owner}/{repo}")
        
        # 1. Prepare repository file tree snippet
        tree_snippet = "\n".join([
            f"- {f['path']} ({f.get('priority', 'Low')} priority)" 
            for f in file_tree[:100]  # limit list to prevent token overload
        ])
        if len(file_tree) > 100:
            tree_snippet += f"\n... and {len(file_tree) - 100} more files."

        # 2. Prepare high-priority summaries snippet
        summaries_snippet = ""
        for item in high_priority_file_summaries[:15]:
            summaries_snippet += f"File: {item['path']}\nContent summary:\n{item['summary']}\n\n"

        # 3. Truncate README content if too large
        readme_snippet = readme_content[:4000] if readme_content else "No README.md found in repository root."

        prompt = f"""
Analyze the file tree and contents of the key files of the repository '{owner}/{repo}' and output a highly detailed, structured, production-grade architecture report in JSON format.

Below is the repository metadata:
- Owner: {owner}
- Repo: {repo}

=== REPOSITORY TREE ===
{tree_snippet}

=== README SNIPPET ===
{readme_snippet}

=== CORE FILE SUMMARIES ===
{summaries_snippet}

Generate a JSON object containing the following keys. Do NOT wrap it in any text other than the JSON block.
Ensure all values are written in valid Markdown.

JSON Schema:
{{
  "purpose": "A clear, compelling summary of what the repository does and its business value.",
  "tech_stack": "List of core programming languages, frameworks, vector databases, third-party APIs used, and details.",
  "architecture_overview": "Comprehensive design patterns used (MVC, Microservices, Clean Architecture, etc.) and codebase organization.",
  "execution_flow": "Step-by-step trace of how the code initializes and what happens when it runs.",
  "api_structure": "Endpoints, routing patterns, or key modules controlling APIs (if applicable).",
  "database_structure": "Database models, schemas, pgvector details, or local storage structures (if applicable).",
  "service_interactions": "How components communicate (e.g. backend to frontend, DB queries, third-party integrations).",
  "beginner_explanation": "A simplified, non-technical explanation of how the project works.",
  "intermediate_explanation": "An explanation suitable for a junior/mid-level developer focusing on files and libraries.",
  "expert_explanation": "A deep dive explanation for a principal engineer detailing concurrency, bottlenecks, design choices, and scaling."
}}
"""
        
        messages = [
            {"role": "system", "content": "You are a senior enterprise software architect who writes detailed technical architecture reports in JSON."},
            {"role": "user", "content": prompt}
        ]
        
        raw_response = await self.groq_client.get_chat_response(messages, temperature=0.1)
        
        # Extract JSON from response
        try:
            # Strip code fence blocks if any
            clean_response = raw_response.strip()
            if clean_response.startswith("```json"):
                clean_response = clean_response[7:]
            if clean_response.endswith("```"):
                clean_response = clean_response[:-3]
            clean_response = clean_response.strip()
            
            data = json.loads(clean_response, strict=False)
            logger.info("Successfully generated and parsed architecture report.")
            return data
        except Exception as e:
            logger.error(f"Failed to parse JSON architecture report: {e}. Raw response: {raw_response[:500]}")
            # Fallback structure
            return {
                "purpose": "Failed to generate structured report. Raw output follows.",
                "tech_stack": "Unknown",
                "architecture_overview": raw_response,
                "execution_flow": "Unknown",
                "api_structure": "Unknown",
                "database_structure": "Unknown",
                "service_interactions": "Unknown",
                "beginner_explanation": "Failed to generate custom explanation.",
                "intermediate_explanation": "Failed to generate custom explanation.",
                "expert_explanation": raw_response
            }
