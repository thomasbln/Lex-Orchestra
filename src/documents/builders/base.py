from __future__ import annotations
from abc import ABC, abstractmethod
from src.documents.content_models import BuildContext


class DocumentBuilder(ABC):

    @abstractmethod
    def build(
        self,
        graph_result: dict,
        reasoning_result: dict,
        config: dict,
        gap_hints: list,
        ctx: BuildContext,
    ) -> object:
        """Return a ContentModel dataclass. Never return raw graph data."""
        ...

    def _required_gaps_for(self, doc_type: str, gap_hints: list) -> list:
        return [
            g for g in gap_hints
            if getattr(g, "severity", "RECOMMENDED") == "REQUIRED"
            and doc_type in (getattr(g, "doc_affected", None) or [])
        ]
