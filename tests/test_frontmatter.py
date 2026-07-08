from pathlib import Path

import pytest

from skill_doctor.frontmatter import FrontmatterError, parse_skill_markdown


def test_parse_skill_markdown_returns_metadata_and_body(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name: useful-skill
description: Use when reviewing Agent Skills for quality and trigger precision.
---

# Useful Skill

Run the scanner and explain the report.
""",
        encoding="utf-8",
    )

    document = parse_skill_markdown(skill_file)

    assert document.metadata == {
        "name": "useful-skill",
        "description": "Use when reviewing Agent Skills for quality and trigger precision.",
    }
    assert document.body.startswith("# Useful Skill")


def test_parse_skill_markdown_rejects_missing_frontmatter(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text("# Missing frontmatter\n", encoding="utf-8")

    with pytest.raises(FrontmatterError, match="frontmatter"):
        parse_skill_markdown(skill_file)


def test_parse_skill_markdown_rejects_malformed_frontmatter_line(tmp_path: Path) -> None:
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(
        """---
name useful-skill
description: Broken metadata.
---
""",
        encoding="utf-8",
    )

    with pytest.raises(FrontmatterError, match="line 2"):
        parse_skill_markdown(skill_file)
