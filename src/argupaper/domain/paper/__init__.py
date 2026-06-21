"""Paper structure extraction domain logic."""

from argupaper.domain.paper.structured import StructuredExtractor
from argupaper.domain.paper.title import PaperTitleResolver, PaperTitleResult

__all__ = ["PaperTitleResolver", "PaperTitleResult", "StructuredExtractor"]
