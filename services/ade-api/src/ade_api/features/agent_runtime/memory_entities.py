"""Prepared related identity shared by memory review bindings."""

from dataclasses import dataclass


@dataclass(frozen=True)
class NewEntity:
    id: str
    kind: str
    label: str
