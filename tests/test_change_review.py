from dataclasses import replace
from pathlib import Path

import pytest

from skill_doctor.change_models import ResourceSnapshot, SnapshotSet
from skill_doctor.change_review import compare_snapshots
from skill_doctor.models import Finding
from skill_doctor.snapshot import snapshot_target


@pytest.fixture
def baseline(tmp_path: Path):
    directory = tmp_path / "review-api"
    directory.mkdir()
    (directory / "SKILL.md").write_text(
        "---\nname: review-api\ndescription: Use when reviewing API changes for compatibility risks.\n"
        "allowed-tools: Read\n---\n# Review\nInspect API changes.\n", encoding="utf-8",
    )
    return snapshot_target(tmp_path)


def compare(baseline, **updates):
    current = replace(baseline, skills=(replace(baseline.skills[0], **updates),))
    return compare_snapshots(baseline, current, base_ref="main", target="skills")


def test_no_change(baseline):
    report = compare_snapshots(baseline, baseline, base_ref="main", target="skills")
    assert report.overall_risk == "none"
    assert report.changes == ()


@pytest.mark.parametrize("updates,risk,reason", [
    ({"allowed_tools": ("*",)}, "high", "Wildcard"),
    ({"allowed_tools": ("Read", "Write")}, "high", "Tool permissions expanded"),
    ({"allowed_tools": ()}, "high", "restriction removed"),
    ({"body_sha256": "changed"}, "low", "Instructions changed"),
    ({"body_nonempty_lines": 12}, "medium", "Instruction size"),
    ({"body_word_count": 100}, "medium", "Instruction size"),
    ({"body_nonempty_lines": 11}, "low", "Instructions changed"),
    ({"trigger_terms": ("api", "compatibility", "reviewing", "risks", "breaking", "schema")}, "medium", "Trigger terms"),
    ({"score": 90, "grade": "A"}, "medium", "Quality score"),
    ({"score": 99}, "low", "Quality"),
    ({"resources": (ResourceSnapshot("scripts/run.py", "scripts", "abc"),)}, "medium", "Script added"),
    ({"resources": (ResourceSnapshot("references/a.md", "references", "abc"),)}, "low", "Resource added"),
    ({"resources": (ResourceSnapshot("assets/a.png", "assets", "abc"),)}, "low", "Resource added"),
])
def test_risk_rules(baseline, updates, risk, reason):
    report = compare(baseline, **updates)
    assert report.overall_risk == risk
    assert any(reason in text for text in report.changes[0].reasons)


@pytest.mark.parametrize("code,severity,risk", [
    ("missing-name", "error", "high"),
    ("description-too-broad", "warning", "high"),
    ("missing-trigger-context", "warning", "high"),
    ("orphan-resource", "info", "low"),
])
def test_new_findings(baseline, code, severity, risk):
    finding = Finding(severity, code, "review-api/SKILL.md", "Problem", "Fix")
    report = compare(baseline, findings=(finding,))
    assert report.overall_risk == risk
    assert report.changes[0].findings_introduced == (finding,)


def test_resources_removed_and_modified(baseline):
    original = ResourceSnapshot("references/a.md", "references", "old")
    baseline = replace(baseline, skills=(replace(baseline.skills[0], resources=(original,)),))
    removed = compare(baseline, resources=())
    assert removed.overall_risk == "medium"
    assert removed.changes[0].resources_removed == (original,)
    changed = replace(original, sha256="new")
    modified = compare(baseline, resources=(changed,))
    assert modified.overall_risk == "low"
    assert modified.changes[0].resources_modified == (changed,)


def test_script_modified(baseline):
    script = ResourceSnapshot("scripts/run.py", "scripts", "old")
    baseline = replace(baseline, skills=(replace(baseline.skills[0], resources=(script,)),))
    assert compare(baseline, resources=(replace(script, sha256="new"),)).overall_risk == "medium"


def test_findings_resolved_and_path_only_move(baseline):
    finding = Finding("warning", "missing-resource", "review-api/SKILL.md", "Missing", "Fix")
    baseline = replace(baseline, skills=(replace(baseline.skills[0], findings=(finding,), score=90),))
    improved = compare(baseline, findings=(), score=100)
    assert improved.overall_risk == "low"
    assert improved.changes[0].findings_resolved == (finding,)
    moved = compare(baseline, relative_path="nested/review-api", findings=(replace(finding, path="nested/review-api/SKILL.md"),))
    assert moved.summary.skills_moved == 1
    assert moved.summary.skills_modified == 0
    assert moved.changes[0].findings_introduced == ()


def test_added_removed_and_highest_risk(baseline):
    empty = SnapshotSet((), 100, "A+")
    added = compare_snapshots(empty, baseline, base_ref="main", target="skills")
    assert added.overall_risk == "high"  # Explicit permissions require review even for new skills.
    clean = replace(baseline, skills=(replace(baseline.skills[0], allowed_tools=()),))
    assert compare_snapshots(empty, clean, base_ref="main", target="skills").overall_risk == "low"
    removed = compare_snapshots(baseline, empty, base_ref="main", target="skills")
    assert removed.overall_risk == "high"
    assert removed.summary.skills_removed == 1


def test_growth_threshold_boundary(baseline):
    baseline = replace(baseline, skills=(replace(baseline.skills[0], body_nonempty_lines=40),))
    assert compare(baseline, body_nonempty_lines=50).overall_risk == "low"
    assert compare(baseline, body_nonempty_lines=51).overall_risk == "medium"


def test_trigger_ratio_boundary(baseline):
    baseline = replace(baseline, skills=(replace(baseline.skills[0], trigger_terms=("one", "two", "three", "four")),))
    assert compare(baseline, trigger_terms=("one", "two", "three", "five")).overall_risk == "medium"
    assert compare(baseline, trigger_terms=("one", "two", "three", "four", "five")).overall_risk == "low"
