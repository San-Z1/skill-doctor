import json

from skill_doctor.models import Finding, Report
from skill_doctor.reporting import render_github, render_json, render_markdown, render_sarif


def sample_report() -> Report:
    return Report(
        root="/repo/skills",
        skills_scanned=2,
        findings=[
            Finding(
                severity="warning",
                code="description-too-broad",
                path="broad-skill",
                message="Description appears broad enough to trigger for unrelated work.",
                suggestion="Narrow the description.",
            )
        ],
    )


def test_render_markdown_includes_summary_and_findings() -> None:
    output = render_markdown(sample_report())

    assert "# Skill Doctor Report" in output
    assert "Skills scanned: 2" in output
    assert "`description-too-broad`" in output
    assert "Narrow the description." in output


def test_render_json_is_machine_readable() -> None:
    output = render_json(sample_report())

    parsed = json.loads(output)
    assert parsed["root"] == "/repo/skills"
    assert parsed["skills_scanned"] == 2
    assert parsed["findings"][0]["code"] == "description-too-broad"


def test_render_sarif_outputs_code_scanning_log() -> None:
    output = render_sarif(sample_report())

    parsed = json.loads(output)
    assert parsed["version"] == "2.1.0"
    run = parsed["runs"][0]
    assert run["tool"]["driver"]["name"] == "Skill Doctor"
    assert run["tool"]["driver"]["rules"][0]["id"] == "description-too-broad"
    result = run["results"][0]
    assert result["ruleId"] == "description-too-broad"
    assert result["level"] == "warning"
    assert result["locations"][0]["physicalLocation"]["artifactLocation"]["uri"] == "broad-skill"


def test_render_markdown_shows_clean_result() -> None:
    output = render_markdown(Report(root="/repo/skills", skills_scanned=1, findings=[]))

    assert "No findings." in output


def test_render_github_outputs_actions_annotations() -> None:
    output = render_github(sample_report())

    assert output == (
        "::warning file=broad-skill,title=description-too-broad::"
        "Description appears broad enough to trigger for unrelated work. "
        "Suggestion: Narrow the description.\n"
    )


def test_render_github_escapes_annotation_control_characters() -> None:
    report = Report(
        root="/repo/skills",
        skills_scanned=1,
        findings=[
            Finding(
                severity="error",
                code="bad:code",
                path="weird,file\npath",
                message="Line one\nLine two",
                suggestion="Use 50% fewer, broader triggers.",
            )
        ],
    )

    output = render_github(report)

    assert "%0A" in output
    assert "%2C" in output
    assert "%25" in output
    assert output.startswith("::error ")
