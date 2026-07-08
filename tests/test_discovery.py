from pathlib import Path

from skill_doctor.discovery import discover_skills


def write_skill(path: Path, name: str, description: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"""---
name: {name}
description: {description}
---

# {name}
""",
        encoding="utf-8",
    )


def test_discover_skills_from_single_skill_directory(tmp_path: Path) -> None:
    write_skill(
        tmp_path,
        "api-review",
        "Use when reviewing API-oriented Agent Skills for trigger precision.",
    )

    skills = discover_skills(tmp_path)

    assert [skill.name for skill in skills] == ["api-review"]
    assert skills[0].path == tmp_path
    assert skills[0].skill_file == tmp_path / "SKILL.md"


def test_discover_skills_from_collection_directory(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "one",
        "one",
        "Use when checking one specific skill workflow.",
    )
    write_skill(
        tmp_path / "two",
        "two",
        "Use when checking another specific skill workflow.",
    )

    skills = discover_skills(tmp_path)

    assert [skill.name for skill in skills] == ["one", "two"]


def test_discover_skills_from_skill_file(tmp_path: Path) -> None:
    write_skill(
        tmp_path / "file-skill",
        "file-skill",
        "Use when checking a single SKILL.md file.",
    )

    skills = discover_skills(tmp_path / "file-skill" / "SKILL.md")

    assert [skill.name for skill in skills] == ["file-skill"]
