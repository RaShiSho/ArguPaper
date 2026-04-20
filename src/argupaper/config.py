"""Configuration management for ArguPaper."""

import os
from pathlib import Path
from typing import Optional

from pydantic import BaseModel
from dotenv import load_dotenv

# Load .env file
load_dotenv()


class PDFConfig(BaseModel):
    """PDF processing configuration."""
    api_key: str
    api_endpoint: str = "https://mineru.net/api/v4/extract/task"
    cache_dir: str = "./data/cache"
    public_url_base: Optional[str] = None  # e.g., "https://xxxx.ngrok-free.dev" for ngrok


class RetrievalConfig(BaseModel):
    """Retrieval module configuration."""
    semantic_scholar_api_key: Optional[str] = None


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


def load_config() -> Config:
    """Load configuration from environment variables.

    Raises:
        ValueError: If required configuration is missing.

    Returns:
        Config object with all settings.
    """
    # PDF config is required
    pdf_api_key = os.getenv("MINERU_API_KEY", "")
    if not pdf_api_key:
        raise ValueError(
            "MINERU_API_KEY not set. Please set it in .env file or environment."
        )

    pdf_endpoint = os.getenv("MINERU_API_ENDPOINT", "https://mineru.net/api/v4/extract/task")
    pdf_cache_dir = os.getenv("CACHE_PATH", "./data/cache")

    # Create data directory if it doesn't exist
    Path(pdf_cache_dir).mkdir(parents=True, exist_ok=True)

    return Config(
        pdf=PDFConfig(
            api_key=pdf_api_key,
            api_endpoint=pdf_endpoint,
            cache_dir=pdf_cache_dir,
            public_url_base=os.getenv("NGROK_URL_BASE"),
        ),
        retrieval=RetrievalConfig(
            semantic_scholar_api_key=os.getenv("SEMANTIC_SCHOLAR_API_KEY"),
        ),
        model=ModelConfig(
            model=os.getenv("LLM_MODEL", "claude-3-5-sonnet-20241022"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
        ),
        debate=DebateConfig(
            max_rounds=int(os.getenv("DEBATE_MAX_ROUNDS", "3")),
        ),
        data_path=os.getenv("DATA_PATH", "./data"),
    )
