"""
LLM and embedding provider selection via env.
Set LLM_PROVIDER=gemini and GOOGLE_API_KEY to use Gemini instead of OpenAI.
Set EMBEDDING_PROVIDER=gemini to use Gemini embeddings (1536 dims for pgvector).
"""
import os
from langchain_core.language_models import BaseChatModel

def get_llm():
    provider = (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[reportMissingImports]
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        return ChatGoogleGenerativeAI(model=model, temperature=0.2)
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

def get_llm_json():
    """LLM that returns JSON (for Detective node)."""
    provider = (os.environ.get("LLM_PROVIDER") or "openai").strip().lower()
    if provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI  # type: ignore[reportMissingImports]
        model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
        llm = ChatGoogleGenerativeAI(model=model, temperature=0.2)
        # Gemini: ask for JSON in prompt; no bind(response_format) like OpenAI
        return llm
    else:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model="gpt-4o-mini", temperature=0.2).bind(response_format={"type": "json_object"})
