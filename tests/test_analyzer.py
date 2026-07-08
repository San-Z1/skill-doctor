from pathlib import Path

from skill_doctor.analyzer import analyze_skills
from skill_doctor.discovery import discover_skills


def write_skill(
    path: Path,
    *,
    name: str = "demo-skill",
    description: str = "Use when checking one specific Agent Skill workflow.",
    body: str = "# Demo Skill\n\nFollow the focused workflow.",
    extra_frontmatter: str = "",
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"""---
name: {name}
description: {description}
{extra_frontmatter}---

{body}
""",
        encoding="utf-8",
    )


def codes(report) -> set[str]:
    return {finding.code for finding in report.findings}


def test_analyzer_flags_invalid_metadata_and_folder_mismatch(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "folder-name",
        name="Bad Name",
        description="Too short.",
    )

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    assert "missing-trigger-context" in codes(report)
    assert "invalid-skill-name" in codes(report)
    assert "folder-name-mismatch" in codes(report)


def test_analyzer_flags_overly_broad_description(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "broad-helper",
        name="broad-helper",
        description="Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    assert "description-too-broad" in codes(report)


def test_analyzer_flags_large_body_without_references(tmp_path: Path) -> None:
    body = "\n".join(f"Line {index}" for index in range(12))
    write_skill(tmp_path / "large-skill", name="large-skill", body=body)

    report = analyze_skills(
        discover_skills(tmp_path),
        root=tmp_path,
        body_line_limit=5,
    )

    assert "body-too-large" in codes(report)


def test_analyzer_flags_orphaned_resource_files(tmp_path: Path) -> None:
    skill_dir = tmp_path / "resource-skill"
    write_skill(skill_dir, name="resource-skill", body="# Resource Skill\n\nNo resource mention.")
    (skill_dir / "scripts").mkdir()
    (skill_dir / "scripts" / "helper.py").write_text("print('helper')\n", encoding="utf-8")
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "guide.md").write_text("# Guide\n", encoding="utf-8")

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    orphan_paths = {finding.path for finding in report.findings if finding.code == "orphan-resource"}
    assert "resource-skill/scripts/helper.py" in orphan_paths
    assert "resource-skill/references/guide.md" in orphan_paths


def test_analyzer_flags_missing_referenced_resource_files(tmp_path: Path) -> None:
    skill_dir = tmp_path / "missing-resource-skill"
    write_skill(
        skill_dir,
        name="missing-resource-skill",
        body=(
            "# Missing Resource Skill\n\n"
            "Read `references/missing.md` before acting.\n"
            "Use [the checklist](references/checklist.md) for detailed review."
        ),
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "checklist.md").write_text("# Checklist\n", encoding="utf-8")

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    missing = [finding for finding in report.findings if finding.code == "missing-resource"]
    assert len(missing) == 1
    assert missing[0].path == "missing-resource-skill/SKILL.md"
    assert "references/missing.md" in missing[0].message


def test_analyzer_flags_overlapping_descriptions(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "api-review",
        name="api-review",
        description="Use when reviewing API skills for trigger precision and quality.",
    )
    write_skill(
        tmp_path / "api-quality",
        name="api-quality",
        description="Use when reviewing API skills for trigger precision and quality issues.",
    )

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    assert "overlapping-description" in codes(report)


def test_analyzer_flags_broad_allowed_tools(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "tool-skill",
        name="tool-skill",
        extra_frontmatter='allowed-tools: "*"\n',
    )

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    assert "allowed-tools-too-broad" in codes(report)


def test_analyzer_allows_good_skill(tmp_path: Path) -> None:
    skill_dir = tmp_path / "focused-review"
    write_skill(
        skill_dir,
        name="focused-review",
        description="Use when reviewing an Agent Skill for trigger precision, resource references, and publish readiness.",
        body="# Focused Review\n\nRead references/checklist.md when the user asks for detailed scoring.",
    )
    (skill_dir / "references").mkdir()
    (skill_dir / "references" / "checklist.md").write_text("# Checklist\n", encoding="utf-8")

    report = analyze_skills(discover_skills(tmp_path), root=tmp_path)

    assert report.skills_scanned == 1
    assert report.findings == []
