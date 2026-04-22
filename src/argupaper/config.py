"""Configuration management for ArguPaper."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load .env file
load_dotenv()


class PDFConfig(BaseModel):
    """PDF processing configuration."""

    api_key: str
    api_endpoint: str = "https://mineru.net/api/v4/extract/task"
    cache_dir: str = "./data/cache"
    public_url_base: Optional[str] = None


class RetrievalConfig(BaseModel):
    """Retrieval module configuration."""

    semantic_scholar_api_key: Optional[str] = None
    default_limit: int = 10
    max_results: int = 20


class LLMProviderConfig(BaseModel):
    """Configuration for one OpenAI-compatible LLM provider."""

    name: str
    base_url: str
    api_key: str
    model: str


class ModelConfig(BaseModel):
    """LLM model configuration."""

    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096
    default_provider: str = "default"
    weak_provider: str = "weak"
    providers: dict[str, LLMProviderConfig] = Field(default_factory=dict)


class SearchAgentConfig(BaseModel):
    """Search-agent specific configuration."""

    trace_path: str = "./data/agent_runs/search"
    max_candidates: int = 50


class DebateConfig(BaseModel):
    """Debate configuration."""

    max_rounds: int = 3


class Config(BaseModel):
    """Main configuration for ArguPaper."""

    pdf: PDFConfig
    retrieval: RetrievalConfig = RetrievalConfig()
    model: ModelConfig = ModelConfig()
    search_agent: SearchAgentConfig = SearchAgentConfig()
    debate: DebateConfig = DebateConfig()
    data_path: str = "./data"
    analyze_enable_retrieval_loop: bool = True


def _load_llm_providers() -> dict[str, LLMProviderConfig]:
    """Load OpenAI-compatible provider configs from environment variables."""

    grouped: dict[str, dict[str, str]] = {}
    prefix = "LLM_PROVIDER__"
    for key, value in os.environ.items():
        if not key.startswith(prefix):
            continue

        remainder = key[len(prefix) :]
        parts = remainder.split("__", 1)
        if len(parts) != 2:
            continue

        provider_name, field_name = parts
        normalized_name = provider_name.strip().lower()
        grouped.setdefault(normalized_name, {})[field_name.strip().lower()] = value

    providers: dict[str, LLMProviderConfig] = {}
    for name, fields in grouped.items():
        base_url = fields.get("base_url")
        api_key = fields.get("api_key")
        model = fields.get("model")
        if not base_url or not api_key or not model:
            continue
        providers[name] = LLMProviderConfig(
            name=name,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            model=model,
        )
    return providers


def load_config(require_pdf_api_key: bool = True) -> Config:
    """Load configuration from environment variables."""

    pdf_api_key = os.getenv("MINERU_API_KEY", "")
    if require_pdf_api_key and not pdf_api_key:
        raise ValueError(
            "MINERU_API_KEY not set. Please set it in .env file or environment."
        )

    pdf_endpoint = os.getenv("MINERU_API_ENDPOINT", "https://mineru.net/api/v4/extract/task")
    pdf_cache_dir = os.getenv("CACHE_PATH", "./data/cache")
    data_path = os.getenv("DATA_PATH", "./data")
    search_agent_trace_path = os.getenv("SEARCH_AGENT_TRACE_PATH", "./data/agent_runs/search")

    Path(pdf_cache_dir).mkdir(parents=True, exist_ok=True)
    Path(data_path).mkdir(parents=True, exist_ok=True)
    Path(search_agent_trace_path).mkdir(parents=True, exist_ok=True)

    return Config(
        pdf=PDFConfig(
            api_key=pdf_api_key,
            api_endpoint=pdf_endpoint,
            cache_dir=pdf_cache_dir,
            public_url_base=os.getenv("NGROK_URL_BASE"),
        ),
        retrieval=RetrievalConfig(
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
            default_limit=int(os.getenv("SEARCH_DEFAULT_LIMIT", "10")),
            max_results=int(os.getenv("SEARCH_MAX_RESULTS", "20")),
        ),
        model=ModelConfig(
            model=os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            default_provider=os.getenv("LLM_DEFAULT_PROVIDER", "default"),
            weak_provider=os.getenv("LLM_WEAK_PROVIDER", "weak"),
            providers=_load_llm_providers(),
        ),
        search_agent=SearchAgentConfig(
            trace_path=search_agent_trace_path,
            max_candidates=int(os.getenv("SEARCH_AGENT_MAX_CANDIDATES", "50")),
        ),
        debate=DebateConfig(
            max_rounds=int(os.getenv("DEBATE_MAX_ROUNDS", "3")),
        ),
        data_path=data_path,
        analyze_enable_retrieval_loop=(
            os.getenv("ANALYZE_ENABLE_RETRIEVAL_LOOP", "true").lower() == "true"
        ),
    )
