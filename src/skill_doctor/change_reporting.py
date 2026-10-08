from __future__ import annotations

import html
import json
from dataclasses import asdict
from pathlib import PurePosixPath

from .change_models import ChangeReport
from .reporting import _escape_annotation_message, _escape_annotation_property


def _code(value) -> str:
    value = html.escape(str(value)).replace("\n", " ").replace("\r", " ")
    fence = "`"
    while fence in value:
        fence += "`"
    return f"{fence} {value} {fence}"


def render_change_json(report: ChangeReport) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"


def render_change_markdown(report: ChangeReport) -> str:
    summary = report.summary
    lines = [
        "# Skill Doctor Change Review", "",
        f"- Baseline: {_code(report.base_ref)}", f"- Target: {_code(report.target)}",
        f"- Overall risk: **{report.overall_risk.upper()}**",
        f"- Skills changed: {len(report.changes)} ({summary.skills_added} added, {summary.skills_removed} removed, "
        f"{summary.skills_modified} modified, {summary.skills_moved} moved)",
        f"- Quality score: {report.baseline_score} -> {report.current_score} "
        f"({report.current_score - report.baseline_score:+d})", "",
    ]
    if not report.changes:
        return "\n".join(lines) + "No changes detected.\n"
    for change in report.changes:
        lines.extend([
            f"## {_code(change.name or change.new_path or change.old_path)}: {change.kind} / {change.risk.upper()}", "",
            f"- Path: {_code(change.old_path or '(new)')} -> {_code(change.new_path or '(removed)')}",
            f"- Quality: {change.score_before if change.score_before is not None else '-'} "
            f"({change.grade_before or '-'}) -> {change.score_after if change.score_after is not None else '-'} ({change.grade_after or '-'})",
            f"- Instructions: {change.lines_before} -> {change.lines_after} non-empty lines; "
            f"{change.words_before} -> {change.words_after} words",
        ])
        if change.description_before != change.description_after:
            lines.extend([f"- Description before: {_code(change.description_before or '(none)')}",
                          f"- Description after: {_code(change.description_after or '(none)')}"])
        for title, values in (
            ("Trigger terms added", change.trigger_terms_added), ("Trigger terms removed", change.trigger_terms_removed),
            ("Tools added", change.tools_added), ("Tools removed", change.tools_removed),
            ("Resources added", tuple(item.path for item in change.resources_added)),
            ("Resources removed", tuple(item.path for item in change.resources_removed)),
            ("Resources modified", tuple(item.path for item in change.resources_modified)),
        ):
            if values:
                lines.append(f"- {title}: " + ", ".join(_code(value) for value in values))
        for title, findings in (("Introduced", change.findings_introduced), ("Resolved", change.findings_resolved)):
            for finding in findings:
                lines.append(f"- {title} {_code(finding.code)}: {_code(finding.message)}")
        lines.extend(["", "Risk evidence:"])
        lines.extend(f"- {_code(reason)}" for reason in change.reasons)
        lines.append("")
    lines.append("Static review only. Risk levels are change-review heuristics, not a security verdict.")
    return "\n".join(lines) + "\n"


def render_change_github(report: ChangeReport) -> str:
    lines = []
    for change in report.changes:
        if change.risk not in {"high", "medium"}:
            continue
        target = PurePosixPath(report.target)
        if target.name != "SKILL.md":
            target = target / (change.new_path or change.old_path or ".") / "SKILL.md"
        level = "error" if change.risk == "high" else "warning"
        title = _escape_annotation_property(f"Skill change: {change.name} ({change.risk})")
        path = _escape_annotation_property(target.as_posix())
        message = _escape_annotation_message(" ".join(change.reasons))
        lines.append(f"::{level} file={path},title={title}::{message}")
    notice = _escape_annotation_message(
        f"Skill change review: {len(report.changes)} changed, overall risk {report.overall_risk}."
    )
    lines.append(f"::notice title=Skill Doctor change review::{notice}")
    return "\n".join(lines) + "\n"
