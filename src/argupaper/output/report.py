"""Report generation from analysis results."""

from argupaper.output.structures import ResearchReport


class ReportGenerator:
    """Generates formatted research reports."""

    def __init__(self):
        pass

    async def generate(self, analysis_result: dict) -> ResearchReport:
        """Generate research report from analysis results."""
        raise NotImplementedError("To be implemented")

    def format_markdown(self, report: ResearchReport) -> str:
        """Format report as markdown string."""
        raise NotImplementedError("To be implemented")