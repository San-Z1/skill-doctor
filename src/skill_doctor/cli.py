from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .analyzer import analyze_skills
from .config import FORMATS, SEVERITIES, ConfigError, load_config
from .discovery import discover_skills
from .frontmatter import FrontmatterError
from .reporting import render_github, render_json, render_markdown, render_sarif
from .change_models import RISK_RANK, risk_at_least
from .change_reporting import render_change_github, render_change_json, render_change_markdown
from .git_baseline import review_target


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "diff":
        return _diff_main(argv[1:])
    parser = argparse.ArgumentParser(
        prog="skill-doctor",
        description="Diagnose Agent Skill quality issues before publishing or installing.",
    )
    parser.add_argument("target", help="Path to a SKILL.md, skill directory, or skills collection")
    parser.add_argument(
        "--format",
        choices=tuple(sorted(FORMATS)),
        default=None,
        help="Report output format",
    )
    parser.add_argument(
        "--body-line-limit",
        type=int,
        default=None,
        help="Non-empty SKILL.md body line threshold before progressive-disclosure warning",
    )
    parser.add_argument(
        "--fail-on",
        choices=tuple(sorted(SEVERITIES)),
        default=None,
        help="Lowest finding severity that should produce exit code 1",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional JSON config file with format, fail_on, and body_line_limit",
    )
    args = parser.parse_args(argv)

    target = Path(args.target)
    try:
        config = load_config(args.config)
        output_format = args.format or config.format or "markdown"
        fail_on = args.fail_on or config.fail_on or "error"
        body_line_limit = args.body_line_limit or config.body_line_limit or 180
        skills = discover_skills(target)
        report = analyze_skills(skills, root=target if target.is_dir() else target.parent, body_line_limit=body_line_limit)
    except (ConfigError, FileNotFoundError, FrontmatterError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    output = _render_report(report, output_format)
    print(output, end="")
    return 1 if _has_failing_finding(report.findings, fail_on) else 0


def _positive_int(value: str) -> int:
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Must be a positive integer")
    return number


def _diff_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="skill-doctor diff", description="Review Skill changes against a Git commit.")
    parser.add_argument("target", help="Path to a SKILL.md, skill directory, or skills collection")
    parser.add_argument("--base-ref", required=True, help="Git baseline commit or ref")
    parser.add_argument("--format", choices=("markdown", "json", "github"), default="markdown")
    parser.add_argument("--fail-on-risk", choices=tuple(RISK_RANK), default="none")
    parser.add_argument("--body-line-limit", type=_positive_int, default=180)
    args = parser.parse_args(argv)
    try:
        report = review_target(Path(args.target), args.base_ref, body_line_limit=args.body_line_limit)
    except (ValueError, OSError, FrontmatterError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    renderer = {"markdown": render_change_markdown, "json": render_change_json, "github": render_change_github}[args.format]
    print(renderer(report), end="")
    return 1 if risk_at_least(report.overall_risk, args.fail_on_risk) else 0


def _render_report(report, output_format: str) -> str:
    if output_format == "json":
        return render_json(report)
    if output_format == "github":
        return render_github(report)
    if output_format == "sarif":
        return render_sarif(report)
    return render_markdown(report)


def _has_failing_finding(findings, fail_on: str) -> bool:
    severity_rank = {"info": 1, "warning": 2, "error": 3}
    threshold = severity_rank[fail_on]
    return any(severity_rank.get(finding.severity, 0) >= threshold for finding in findings)
