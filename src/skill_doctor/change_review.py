from __future__ import annotations

from .change_models import (
    RISK_RANK, ChangeReport, ChangeSummary, SkillChange, SkillSnapshot, SnapshotSet,
)


def compare_snapshots(
    baseline: SnapshotSet, current: SnapshotSet, *, base_ref: str, target: str,
) -> ChangeReport:
    old = {_identity(skill): skill for skill in baseline.skills}
    new = {_identity(skill): skill for skill in current.skills}
    changes = []
    for key in sorted(old.keys() | new.keys()):
        before, after = old.get(key), new.get(key)
        change = _compare_skill(before, after)
        if change is not None:
            changes.append(change)
    return ChangeReport(
        schema_version=1, base_ref=base_ref, target=target,
        overall_risk=max((change.risk for change in changes), key=RISK_RANK.get, default="none"),
        baseline_score=baseline.score, current_score=current.score,
        summary=ChangeSummary(*(sum(change.kind == kind for change in changes)
                                for kind in ("added", "removed", "modified", "moved"))),
        changes=tuple(changes),
    )


def _identity(skill: SkillSnapshot) -> tuple[str, str]:
    return ("name", skill.name) if skill.name else ("path", skill.relative_path)


def _finding_key(finding, skill):
    path = finding.path
    if path == skill.relative_path:
        path = "."
    elif skill.relative_path != "." and path.startswith(skill.relative_path + "/"):
        path = path[len(skill.relative_path) + 1:]
    return finding.severity, finding.code, path, finding.message


def _compare_skill(before: SkillSnapshot | None, after: SkillSnapshot | None) -> SkillChange | None:
    kind = "added" if before is None else "removed" if after is None else "modified"
    if before and after and before.relative_path != after.relative_path:
        kind = "moved"
    old_terms, new_terms = set(before.trigger_terms if before else ()), set(after.trigger_terms if after else ())
    old_tools, new_tools = set(before.allowed_tools if before else ()), set(after.allowed_tools if after else ())
    old_resources = {resource.path: resource for resource in before.resources} if before else {}
    new_resources = {resource.path: resource for resource in after.resources} if after else {}
    added = tuple(new_resources[path] for path in sorted(new_resources.keys() - old_resources.keys()))
    removed = tuple(old_resources[path] for path in sorted(old_resources.keys() - new_resources.keys()))
    modified = tuple(new_resources[path] for path in sorted(new_resources.keys() & old_resources.keys())
                     if new_resources[path].sha256 != old_resources[path].sha256)
    old_findings = {_finding_key(finding, before): finding for finding in before.findings} if before else {}
    new_findings = {_finding_key(finding, after): finding for finding in after.findings} if after else {}
    introduced = tuple(new_findings[key] for key in sorted(new_findings.keys() - old_findings.keys()))
    resolved = tuple(old_findings[key] for key in sorted(old_findings.keys() - new_findings.keys()))
    instruction_changed = bool(before and after and (
        before.body_sha256 != after.body_sha256
        or before.body_nonempty_lines != after.body_nonempty_lines
        or before.body_word_count != after.body_word_count))
    metadata_changed = bool(before and after and (
        before.metadata_sha256 != after.metadata_sha256 or before.description != after.description))
    quality_changed = bool(before and after and (before.score != after.score or before.grade != after.grade))
    if (kind == "modified" and not any((old_terms != new_terms, old_tools != new_tools, added, removed,
                                        modified, introduced, resolved, instruction_changed, metadata_changed, quality_changed))):
        return None

    evidence: list[tuple[str, str]] = []

    def note(risk: str, reason: str) -> None:
        evidence.append((risk, reason))

    if after is None:
        note("high", "Skill removed.")
    else:
        if "*" in new_tools - old_tools:
            note("high", "Wildcard tool permission added.")
        elif new_tools - old_tools and "*" not in old_tools:
            note("high", "Tool permissions expanded: " + ", ".join(sorted(new_tools - old_tools)) + ".")
        if before and old_tools and not new_tools:
            note("high", "Tool restriction removed; access is no longer explicitly constrained.")
        for finding in introduced:
            if finding.severity == "error" or finding.code in {"description-too-broad", "missing-trigger-context"}:
                note("high", f"New {finding.severity} finding: {finding.code}.")
        for resource in added + modified:
            action = "added" if resource in added else "modified"
            note("medium" if resource.kind == "scripts" else "low",
                 f"{'Script' if resource.kind == 'scripts' else 'Resource'} {action}: {resource.path}.")
        for resource in removed:
            note("medium", f"Resource removed: {resource.path}.")
        if before:
            term_delta = len(old_terms ^ new_terms)
            smaller = min(len(old_terms), len(new_terms))
            if term_delta:
                material = len(new_terms - old_terms) >= 2 or len(old_terms - new_terms) >= 2
                material = material or term_delta / max(1, smaller) >= 0.30
                note("medium" if material else "low", "Trigger terms changed.")
            growth = any(new - old >= 10 and new > old * 1.25 for old, new in (
                (before.body_nonempty_lines, after.body_nonempty_lines),
                (before.body_word_count, after.body_word_count)))
            if growth:
                note("medium", "Instruction size grew by more than 25% and at least 10 lines or words.")
            elif instruction_changed:
                note("low", "Instructions changed below the size-growth threshold.")
            if before.score - after.score >= 10:
                note("medium", f"Quality score dropped {before.score - after.score} points.")
            elif quality_changed or resolved:
                note("low", "Quality findings or score changed.")
        if kind == "added":
            note("low", "Skill added.")
        if kind == "moved":
            note("low", "Skill directory moved.")
        if not evidence:
            note("low", "Skill metadata, tool restrictions, or findings changed.")
    return SkillChange(
        name=(after or before).name, kind=kind,
        old_path=before.relative_path if before else None, new_path=after.relative_path if after else None,
        risk=max((risk for risk, _ in evidence), key=RISK_RANK.get),
        reasons=tuple(reason for _, reason in evidence),
        description_before=before.description if before else None, description_after=after.description if after else None,
        trigger_terms_added=tuple(sorted(new_terms - old_terms)), trigger_terms_removed=tuple(sorted(old_terms - new_terms)),
        tools_added=tuple(sorted(new_tools - old_tools)), tools_removed=tuple(sorted(old_tools - new_tools)),
        resources_added=added, resources_removed=removed, resources_modified=modified,
        findings_introduced=introduced, findings_resolved=resolved,
        score_before=before.score if before else None, score_after=after.score if after else None,
        grade_before=before.grade if before else None, grade_after=after.grade if after else None,
        lines_before=before.body_nonempty_lines if before else 0, lines_after=after.body_nonempty_lines if after else 0,
        words_before=before.body_word_count if before else 0, words_after=after.body_word_count if after else 0,
        instruction_changed=instruction_changed,
    )
