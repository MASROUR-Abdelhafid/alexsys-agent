"""
LLM Factory — Abstraction multi-provider.
"""

import structlog
from config import config

logger = structlog.get_logger(__name__)


def get_llm(temperature: float = 0):
    """Retourne le LLM configuré selon LLM_PROVIDER."""
    provider = config.LLM_PROVIDER.lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        llm = ChatOllama(
            model=config.LLM_MODEL,
            base_url=config.OLLAMA_BASE_URL,
            temperature=temperature,
        )
        logger.info("LLM Ollama initialisé", model=config.LLM_MODEL)
        return llm

    elif provider == "groq":
        from langchain_groq import ChatGroq
        llm = ChatGroq(
            model=config.LLM_MODEL,
            api_key=config.GROQ_API_KEY,
            temperature=temperature,
        )
        logger.info("LLM Groq initialisé", model=config.LLM_MODEL)
        return llm

    elif provider == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=config.LLM_MODEL,
            google_api_key=config.GEMINI_API_KEY,
            temperature=temperature,
            convert_system_message_to_human=True,
        )
        logger.info("LLM Gemini initialisé", model=config.LLM_MODEL)
        return llm

    elif provider == "openai":
        from langchain_openai import ChatOpenAI
        llm = ChatOpenAI(
            model=config.LLM_MODEL,
            temperature=temperature,
            api_key=config.OPENAI_API_KEY,
        )
        logger.info("LLM OpenAI initialisé", model=config.LLM_MODEL)
        return llm

    else:
        raise ValueError(f"Provider inconnu : {provider}")