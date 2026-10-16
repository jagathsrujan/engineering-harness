from __future__ import annotations

from dataclasses import dataclass
from typing import Any

STATUS_UNREVIEWED = "unreviewed"
STATUS_REVIEWED = "reviewed"
STATUS_DISPUTED = "disputed"


@dataclass(slots=True)
class Review:
    status: str = STATUS_UNREVIEWED
    reviewer: str | None = None
    at: str | None = None
    graph_version: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Review:
        return cls(
            status=str(d.get("status", STATUS_UNREVIEWED)),
            reviewer=d.get("reviewer"),
            at=d.get("at"),
            graph_version=d.get("graph_version"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"status": self.status}
        if self.reviewer is not None:
            out["reviewer"] = self.reviewer
        if self.at is not None:
            out["at"] = self.at
        if self.graph_version is not None:
            out["graph_version"] = self.graph_version
        return out
