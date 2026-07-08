from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillDocument:
    path: Path
    metadata: dict[str, str]
    body: str


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    path: Path
    skill_file: Path
    body: str
    metadata: dict[str, str]


@dataclass(frozen=True)
class Finding:
    severity: str
    code: str
    path: str
    message: str
    suggestion: str


@dataclass(frozen=True)
class Report:
    root: str
    skills_scanned: int
    findings: list[Finding]
