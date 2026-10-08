import json
from dataclasses import replace

from skill_doctor.change_reporting import render_change_github, render_change_json, render_change_markdown
from skill_doctor.change_review import compare_snapshots
from test_change_review import baseline, compare


def test_json_versioned_contract_and_evidence(baseline):
    report = compare(baseline, allowed_tools=("Read", "Write"))
    output = json.loads(render_change_json(report))
    assert output["schema_version"] == 1
    assert output["summary"]["skills_modified"] == 1
    assert output["changes"][0]["tools_added"] == ["Write"]
    assert output["overall_risk"] == "high"


def test_markdown_no_changes_and_details(baseline):
    unchanged = compare_snapshots(baseline, baseline, base_ref="main", target="skills")
    assert "No changes" in render_change_markdown(unchanged)
    changed = render_change_markdown(compare(baseline, allowed_tools=("Read", "Write")))
    for expected in ("HIGH", "review-api", "Write", "100", "Tool permissions expanded", "Instructions"):
        assert expected in changed


def test_github_annotations_use_repo_path_and_escape_data(baseline):
    report = compare(baseline, allowed_tools=("Read", "Write"))
    change = replace(report.changes[0], name="bad\n::error::injected", new_path="a,b", reasons=("x%\n::notice::z",))
    output = render_change_github(replace(report, changes=(change,)))
    assert "file=skills/a%2Cb/SKILL.md" in output
    assert "x%25%0A::notice::z" in output
    assert len(output.splitlines()) == 2


def test_markdown_does_not_render_raw_html(baseline):
    report = compare(baseline, description="<img src=x onerror=alert(1)>")
    output = render_change_markdown(report)
    assert "<img" not in output
    assert "&lt;img" in output
