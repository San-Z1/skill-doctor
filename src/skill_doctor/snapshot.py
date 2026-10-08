from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .analyzer import RESOURCE_DIRS, STOPWORDS, analyze_skills
from .change_models import ResourceSnapshot, SkillSnapshot, SnapshotSet
from .discovery import discover_skills
from .models import calculate_quality_score, grade_for_score


def normalize_tools(value: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    depth = 0
    for char in value.strip().strip("[]"):
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if depth == 0 and (char.isspace() or char == ","):
            if current:
                tokens.append("".join(current).strip("\"'"))
                current = []
        else:
            current.append(char)
    if current:
        tokens.append("".join(current).strip("\"'"))
    return tuple(sorted(set(tokens)))


def snapshot_target(target: Path, *, body_line_limit: int = 180) -> SnapshotSet:
    if target.is_symlink():
        raise ValueError(f"Symbolic links are not supported: {target}")
    target = target.resolve()
    root = target.parent if target.is_file() else target
    skills = discover_skills(target)
    names: set[str] = set()
    resources_by_path: dict[Path, tuple[ResourceSnapshot, ...]] = {}
    for skill in skills:
        if skill.name and skill.name in names:
            raise ValueError(f"Duplicate skill name: {skill.name}")
        names.add(skill.name)
        if skill.path.is_symlink() or skill.skill_file.is_symlink():
            raise ValueError(f"Symbolic links are not supported: {skill.path}")
        resources: list[ResourceSnapshot] = []
        for kind in RESOURCE_DIRS:
            directory = skill.path / kind
            paths = [directory, *sorted(directory.rglob("*"))]
            for path in paths:
                if path.is_symlink():
                    raise ValueError(f"Symbolic links are not supported: {path}")
                if path.is_file():
                    resources.append(ResourceSnapshot(
                        path=path.relative_to(skill.path).as_posix(), kind=kind,
                        sha256=_file_hash(path),
                    ))
        resources_by_path[skill.path] = tuple(resources)

    report = analyze_skills(skills, root=root, body_line_limit=body_line_limit)
    snapshots = []
    for skill in skills:
        relative = skill.path.relative_to(root).as_posix()
        findings = tuple(finding for finding in report.findings
                         if relative == "." or finding.path == relative
                         or finding.path.startswith(relative + "/"))
        score = calculate_quality_score(list(findings))
        tools = next((value for key, value in skill.metadata.items()
                      if key.lower() == "allowed-tools"), "")
        snapshots.append(SkillSnapshot(
            name=skill.name, relative_path=relative, description=skill.description,
            trigger_terms=tuple(sorted(set(re.findall(r"\w+", skill.description.lower())) - STOPWORDS)),
            allowed_tools=normalize_tools(tools),
            body_nonempty_lines=sum(bool(line.strip()) for line in skill.body.splitlines()),
            body_word_count=len(skill.body.split()),
            body_sha256=hashlib.sha256(skill.body.encode("utf-8")).hexdigest(),
            metadata_sha256=hashlib.sha256(json.dumps(skill.metadata, sort_keys=True).encode("utf-8")).hexdigest(),
            resources=resources_by_path[skill.path], findings=findings,
            score=score, grade=grade_for_score(score),
        ))
    return SnapshotSet(tuple(snapshots), report.score, report.grade)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
