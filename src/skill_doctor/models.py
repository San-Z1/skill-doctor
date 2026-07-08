from __future__ import annotations

from dataclasses import dataclass, field
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
    score: int = field(init=False)
    grade: str = field(init=False)

    def __post_init__(self) -> None:
        score = calculate_quality_score(self.findings)
        object.__setattr__(self, "score", score)
        object.__setattr__(self, "grade", grade_for_score(score))


def calculate_quality_score(findings: list[Finding]) -> int:
    penalties = {"error": 30, "warning": 10, "info": 2}
    score = 100 - sum(penalties.get(finding.severity, 0) for finding in findings)
    return max(0, score)


def grade_for_score(score: int) -> str:
    if score >= 95:
        return "A+"
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"
