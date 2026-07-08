from __future__ import annotations

import json
from dataclasses import asdict

from .models import Report


def render_markdown(report: Report) -> str:
    lines = [
        "# Skill Doctor Report",
        "",
        f"- Root: `{report.root}`",
        f"- Skills scanned: {report.skills_scanned}",
        f"- Findings: {len(report.findings)}",
        "",
    ]

    if not report.findings:
        lines.append("No findings.")
        return "\n".join(lines) + "\n"

    for finding in report.findings:
        lines.extend(
            [
                f"## {finding.severity.upper()}: `{finding.code}`",
                "",
                f"- Path: `{finding.path}`",
                f"- Message: {finding.message}",
                f"- Suggestion: {finding.suggestion}",
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def render_json(report: Report) -> str:
    return json.dumps(asdict(report), indent=2, sort_keys=True) + "\n"


def render_sarif(report: Report) -> str:
    rules = {}
    results = []
    for finding in report.findings:
        rules.setdefault(
            finding.code,
            {
                "id": finding.code,
                "shortDescription": {"text": finding.code},
                "fullDescription": {"text": finding.suggestion},
                "help": {"text": finding.suggestion},
            },
        )
        results.append(
            {
                "ruleId": finding.code,
                "level": _sarif_level(finding.severity),
                "message": {"text": f"{finding.message} Suggestion: {finding.suggestion}"},
                "locations": [
                    {
                        "physicalLocation": {
                            "artifactLocation": {"uri": finding.path},
                            "region": {"startLine": 1},
                        }
                    }
                ],
            }
        )

    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "Skill Doctor",
                        "informationUri": "https://github.com/skill-doctor/skill-doctor",
                        "rules": list(rules.values()),
                    }
                },
                "results": results,
                "properties": {
                    "skillsScanned": report.skills_scanned,
                    "root": report.root,
                },
            }
        ],
    }
    return json.dumps(sarif, indent=2, sort_keys=True) + "\n"


def render_github(report: Report) -> str:
    lines: list[str] = []
    for finding in report.findings:
        level = "error" if finding.severity == "error" else "warning"
        title = _escape_annotation_property(finding.code)
        path = _escape_annotation_property(finding.path)
        message = _escape_annotation_message(f"{finding.message} Suggestion: {finding.suggestion}")
        lines.append(f"::{level} file={path},title={title}::{message}")
    return "\n".join(lines) + ("\n" if lines else "")


def _escape_annotation_property(value: str) -> str:
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def _escape_annotation_message(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _sarif_level(severity: str) -> str:
    if severity == "error":
        return "error"
    if severity == "warning":
        return "warning"
    return "note"
