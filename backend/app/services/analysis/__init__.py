from app.core.config import settings
from app.services.analysis.base import Analyzer


def get_analyzer() -> Analyzer:
    if settings.ANALYZER == "placeholder":
        from app.services.analysis.placeholder import PlaceholderAnalyzer

        return PlaceholderAnalyzer()
    if settings.ANALYZER == "rag":
        from app.services.analysis.rag import RagAnalyzer

        return RagAnalyzer()
    raise RuntimeError(f"Unknown ANALYZER '{settings.ANALYZER}'")
