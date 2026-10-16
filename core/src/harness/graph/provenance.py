from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Tag(StrEnum):
    ESTIMATED = "estimated"
    ASSUMED = "assumed"
    LOOKED_UP = "looked-up"
    STATED = "stated"
    MEASURED = "measured"
    COMPUTED = "computed"


_WEAKNESS_ORDER: dict[Tag, int] = {
    Tag.ESTIMATED: 0,
    Tag.ASSUMED: 1,
    Tag.LOOKED_UP: 2,
    Tag.STATED: 3,
    Tag.MEASURED: 4,
}


@dataclass(slots=True)
class Provenance:
    tag: Tag
    inherited_weakest: Tag | None = None
    note: str = ""
    source: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Provenance:
        try:
            tag = Tag(d["tag"])
        except KeyError as err:
            raise ValueError("provenance.tag is required") from err
        inherited = d.get("inherited_weakest")
        return cls(
            tag=tag,
            inherited_weakest=Tag(inherited) if inherited is not None else None,
            note=str(d.get("note", "")),
            source=d.get("source"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"tag": self.tag.value}
        if self.inherited_weakest is not None:
            out["inherited_weakest"] = self.inherited_weakest.value
        if self.note:
            out["note"] = self.note
        if self.source is not None:
            out["source"] = self.source
        return out


@dataclass(slots=True)
class SourceRef:
    kind: str
    ref: str
    url: str | None = None

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SourceRef:
        return cls(
            kind=str(d["kind"]),
            ref=str(d["ref"]),
            url=d.get("url"),
        )

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"kind": self.kind, "ref": self.ref}
        if self.url is not None:
            out["url"] = self.url
        return out


def effective_tag(provenance: Provenance) -> Tag:
    return provenance.inherited_weakest or provenance.tag


def weakest_tag(tags: Iterable[Tag | Provenance]) -> Tag | None:
    resolved = {effective_tag(t) if isinstance(t, Provenance) else t for t in tags}
    if not resolved:
        return None
    return sorted(resolved, key=lambda t: _WEAKNESS_ORDER[t])[0]


def inherits_weak_provenance(tag: Tag | None) -> bool:
    return tag in (Tag.ESTIMATED, Tag.ASSUMED)
