from __future__ import annotations

import re
from itertools import combinations
from pathlib import Path

from .models import Finding, Report, Skill


NAME_PATTERN = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")
RESOURCE_DIRS = ("scripts", "references", "assets")
BROAD_WORDS = {
    "anything",
    "everything",
    "all",
    "any",
    "code",
    "docs",
    "tests",
    "files",
    "bugs",
    "reviews",
    "projects",
}
STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "the",
    "to",
    "use",
    "when",
    "with",
    "or",
    "of",
    "in",
    "on",
}


def analyze_skills(
    skills: list[Skill],
    *,
    root: Path,
    body_line_limit: int = 180,
) -> Report:
    findings: list[Finding] = []
    for skill in skills:
        findings.extend(_analyze_single_skill(skill, root, body_line_limit))
    findings.extend(_find_overlaps(skills, root))
    return Report(root=_display_path(root), skills_scanned=len(skills), findings=findings)


def _analyze_single_skill(skill: Skill, root: Path, body_line_limit: int) -> list[Finding]:
    findings: list[Finding] = []
    skill_path = _relative_path(skill.path, root)
    description = skill.description.strip()

    if "name" not in skill.metadata or not skill.name:
        findings.append(
            _finding(
                "error",
                "missing-name",
                skill_path,
                "Skill frontmatter is missing a name.",
                "Add a lowercase kebab-case `name` field to SKILL.md frontmatter.",
            )
        )
    elif not _valid_name(skill.name):
        findings.append(
            _finding(
                "error",
                "invalid-skill-name",
                skill_path,
                f"Skill name `{skill.name}` is not lowercase kebab-case.",
                "Rename the skill with lowercase letters, digits, and hyphens only.",
            )
        )

    if skill.name and skill.path.name != skill.name:
        findings.append(
            _finding(
                "warning",
                "folder-name-mismatch",
                skill_path,
                f"Folder name `{skill.path.name}` does not match skill name `{skill.name}`.",
                "Rename the folder to match the skill name so installs and reviews are predictable.",
            )
        )

    if "description" not in skill.metadata or not description:
        findings.append(
            _finding(
                "error",
                "missing-description",
                skill_path,
                "Skill frontmatter is missing a description.",
                "Add a description that names the task and concrete trigger contexts.",
            )
        )
    else:
        if not _has_trigger_context(description):
            findings.append(
                _finding(
                    "warning",
                    "missing-trigger-context",
                    skill_path,
                    "Description does not clearly say when the skill should be used.",
                    "Start with a phrase like `Use when...` and include concrete task triggers.",
                )
            )
        if _is_overly_broad(description):
            findings.append(
                _finding(
                    "warning",
                    "description-too-broad",
                    skill_path,
                    "Description appears broad enough to trigger for unrelated work.",
                    "Narrow the description to the specific artifacts, workflows, or decisions this skill supports.",
                )
            )

    body_lines = [line for line in skill.body.splitlines() if line.strip()]
    if len(body_lines) > body_line_limit and not (skill.path / "references").exists():
        findings.append(
            _finding(
                "warning",
                "body-too-large",
                _relative_path(skill.skill_file, root),
                f"SKILL.md has {len(body_lines)} non-empty lines and no references directory.",
                "Move detailed examples, checklists, and reference material into `references/` and link to them from SKILL.md.",
            )
        )

    findings.extend(_find_orphan_resources(skill, root))
    findings.extend(_find_tool_warnings(skill, root))
    return findings


def _valid_name(name: str) -> bool:
    return bool(NAME_PATTERN.match(name)) and "--" not in name


def _has_trigger_context(description: str) -> bool:
    lowered = description.lower()
    trigger_phrases = ("use when", "use for", "use this when", "trigger", "when an agent", "when the user")
    return any(phrase in lowered for phrase in trigger_phrases) and len(description.split()) >= 8


def _is_overly_broad(description: str) -> bool:
    lowered = description.lower()
    tokens = set(_tokens(description))
    if "anything" in tokens or "everything" in tokens:
        return True
    return len(tokens & BROAD_WORDS) >= 6 and "," in lowered


def _find_orphan_resources(skill: Skill, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    body_search = f"{skill.body}\n{skill.description}".lower().replace("\\", "/")
    for dirname in RESOURCE_DIRS:
        directory = skill.path / dirname
        if not directory.exists():
            continue
        for resource in sorted(path for path in directory.rglob("*") if path.is_file()):
            relative_to_skill = resource.relative_to(skill.path).as_posix()
            if relative_to_skill.lower() in body_search or resource.name.lower() in body_search:
                continue
            findings.append(
                _finding(
                    "info",
                    "orphan-resource",
                    _relative_path(resource, root),
                    f"Resource `{relative_to_skill}` is not mentioned by SKILL.md.",
                    "Reference the resource from SKILL.md with guidance on when the agent should read or use it.",
                )
            )
    return findings


def _find_tool_warnings(skill: Skill, root: Path) -> list[Finding]:
    allowed_tools = ""
    for key, value in skill.metadata.items():
        if key.lower() == "allowed-tools":
            allowed_tools = value.strip()
            break
    if allowed_tools not in {"*", '"*"', "'*'"}:
        return []
    return [
        _finding(
            "warning",
            "allowed-tools-too-broad",
            _relative_path(skill.skill_file, root),
            "`allowed-tools` allows every tool.",
            "List only the tools required by the workflow, or omit `allowed-tools` when no tool restriction is needed.",
        )
    ]


def _find_overlaps(skills: list[Skill], root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for left, right in combinations(skills, 2):
        left_tokens = set(_tokens(left.description)) - STOPWORDS
        right_tokens = set(_tokens(right.description)) - STOPWORDS
        if len(left_tokens) < 5 or len(right_tokens) < 5:
            continue
        overlap = len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))
        if overlap >= 0.75:
            findings.append(
                _finding(
                    "warning",
                    "overlapping-description",
                    _relative_path(left.path, root),
                    f"`{left.name}` and `{right.name}` have very similar trigger descriptions.",
                    "Make one description narrower or add disambiguating task contexts so agents do not choose both.",
                )
            )
    return findings


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _finding(severity: str, code: str, path: str, message: str, suggestion: str) -> Finding:
    return Finding(
        severity=severity,
        code=code,
        path=path,
        message=message,
        suggestion=suggestion,
    )


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix() or "."
    except ValueError:
        return path.as_posix()


def _display_path(path: Path) -> str:
    return path.resolve().as_posix()
