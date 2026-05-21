"""Load prompt templates from the package prompt directory."""

from pathlib import Path


PROMPTS_ROOT = Path(__file__).resolve().parent


def load_prompt(*parts: str) -> str:
    """Read one prompt file as UTF-8 text."""

    prompt_path = PROMPTS_ROOT.joinpath(*parts)
    try:
        return prompt_path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise FileNotFoundError(f"Prompt file not found or unreadable: {prompt_path}") from exc
