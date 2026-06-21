"""Factories for commonly shared application dependencies."""

from argupaper.config import Config, load_config
from argupaper.memory.paper_store import PaperStore


def get_config(*, require_pdf_api_key: bool = False) -> Config:
    """Load runtime configuration."""

    return load_config(require_pdf_api_key=require_pdf_api_key)


def build_paper_store(config: Config | None = None) -> PaperStore:
    """Build the local paper store from configuration."""

    resolved_config = config or get_config(require_pdf_api_key=False)
    return PaperStore(storage_path=resolved_config.paper_storage_path)


__all__ = ["build_paper_store", "get_config"]

