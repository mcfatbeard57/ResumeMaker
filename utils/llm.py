"""
LLM utilities — Dual-model ChatOllama wrappers with LangSmith tracing.
"""
import os
import yaml
from langchain_ollama import ChatOllama


def setup_langsmith(config: dict) -> None:
    """Configure LangSmith environment variables from config."""
    ls_config = config.get("langsmith", {})
    if ls_config.get("enabled", False):
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = ls_config.get("project_name", "resume-jd-optimizer")
        api_key = ls_config.get("api_key", "")
        if api_key:
            os.environ["LANGCHAIN_API_KEY"] = api_key
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


def get_writer_llm(config: dict) -> ChatOllama:
    """
    Get the Writer agent's LLM (qwen2.5:7b by default).
    Used for creative resume rewriting tasks.
    """
    llm_config = config.get("llm", {})
    setup_langsmith(config)
    return ChatOllama(
        model=llm_config.get("writer_model", "qwen2.5:7b"),
        base_url=llm_config.get("base_url", "http://localhost:11434"),
        temperature=llm_config.get("temperature", 0.3),
        num_predict=llm_config.get("max_tokens", 4096),
    )


def get_reviewer_llm(config: dict) -> ChatOllama:
    """
    Get the Reviewer agent's LLM (llama3.1:8b by default).
    Used for critical evaluation and scoring.
    """
    llm_config = config.get("llm", {})
    setup_langsmith(config)
    return ChatOllama(
        model=llm_config.get("reviewer_model", "llama3.1:8b"),
        base_url=llm_config.get("base_url", "http://localhost:11434"),
        temperature=0.1,  # Lower temp for more consistent scoring
        num_predict=llm_config.get("max_tokens", 4096),
    )


def get_parser_llm(config: dict) -> ChatOllama:
    """
    Get LLM for parsing/analysis tasks. Uses the reviewer model
    for more reliable structured output.
    """
    llm_config = config.get("llm", {})
    setup_langsmith(config)
    return ChatOllama(
        model=llm_config.get("reviewer_model", "llama3.1:8b"),
        base_url=llm_config.get("base_url", "http://localhost:11434"),
        temperature=0.1,
        num_predict=llm_config.get("max_tokens", 4096),
    )


def load_config(config_path: str = "config.yaml") -> dict:
    """Load configuration from YAML file."""
    with open(config_path, "r") as f:
        return yaml.safe_load(f)
