from __future__ import annotations

from dataclasses import dataclass

from .models import Finding


RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}


def risk_at_least(actual: str, threshold: str) -> bool:
    return threshold != "none" and RISK_RANK[actual] >= RISK_RANK[threshold]


@dataclass(frozen=True)
class ResourceSnapshot:
    path: str
    kind: str
    sha256: str


@dataclass(frozen=True)
class SkillSnapshot:
    name: str
    relative_path: str
    description: str
    trigger_terms: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    body_nonempty_lines: int
    body_word_count: int
    body_sha256: str
    metadata_sha256: str
    resources: tuple[ResourceSnapshot, ...]
    findings: tuple[Finding, ...]
    score: int
    grade: str


@dataclass(frozen=True)
class SnapshotSet:
    skills: tuple[SkillSnapshot, ...]
    score: int
    grade: str


@dataclass(frozen=True)
class ChangeSummary:
    skills_added: int
    skills_removed: int
    skills_modified: int
    skills_moved: int


@dataclass(frozen=True)
class SkillChange:
    name: str
    kind: str
    old_path: str | None
    new_path: str | None
    risk: str
    reasons: tuple[str, ...]
    description_before: str | None
    description_after: str | None
    trigger_terms_added: tuple[str, ...]
    trigger_terms_removed: tuple[str, ...]
    tools_added: tuple[str, ...]
    tools_removed: tuple[str, ...]
    resources_added: tuple[ResourceSnapshot, ...]
    resources_removed: tuple[ResourceSnapshot, ...]
    resources_modified: tuple[ResourceSnapshot, ...]
    findings_introduced: tuple[Finding, ...]
    findings_resolved: tuple[Finding, ...]
    score_before: int | None
    score_after: int | None
    grade_before: str | None
    grade_after: str | None
    lines_before: int
    lines_after: int
    words_before: int
    words_after: int
    instruction_changed: bool


@dataclass(frozen=True)
class ChangeReport:
    schema_version: int
    base_ref: str
    target: str
    overall_risk: str
    baseline_score: int
    current_score: int
    summary: ChangeSummary
    changes: tuple[SkillChange, ...]
