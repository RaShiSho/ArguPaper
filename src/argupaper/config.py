"""Configuration management for ArguPaper."""

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import BaseModel

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


class ModelConfig(BaseModel):
    """LLM model configuration."""

    model: str = "claude-3-5-sonnet-20241022"
    temperature: float = 0.7
    max_tokens: int = 4096


class DebateConfig(BaseModel):
    """Debate configuration."""

    max_rounds: int = 3


class Config(BaseModel):
    """Main configuration for ArguPaper."""

    pdf: PDFConfig
    retrieval: RetrievalConfig = RetrievalConfig()
    model: ModelConfig = ModelConfig()
    debate: DebateConfig = DebateConfig()
    data_path: str = "./data"
    analyze_enable_retrieval_loop: bool = True


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

    Path(pdf_cache_dir).mkdir(parents=True, exist_ok=True)
    Path(data_path).mkdir(parents=True, exist_ok=True)

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
        ),
        debate=DebateConfig(
            max_rounds=int(os.getenv("DEBATE_MAX_ROUNDS", "3")),
        ),
        data_path=data_path,
        analyze_enable_retrieval_loop=(
            os.getenv("ANALYZE_ENABLE_RETRIEVAL_LOOP", "true").lower() == "true"
        ),
    )
