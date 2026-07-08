from __future__ import annotations

from pathlib import Path

from .frontmatter import parse_skill_markdown
from .models import Skill


def discover_skills(target: Path) -> list[Skill]:
    target = target.resolve()
    skill_files = _find_skill_files(target)
    skills: list[Skill] = []
    for skill_file in skill_files:
        document = parse_skill_markdown(skill_file)
        metadata = document.metadata
        skills.append(
            Skill(
                name=metadata.get("name", ""),
                description=metadata.get("description", ""),
                path=skill_file.parent,
                skill_file=skill_file,
                body=document.body,
                metadata=metadata,
            )
        )
    return sorted(skills, key=lambda skill: str(skill.path).lower())


def _find_skill_files(target: Path) -> list[Path]:
    if target.is_file():
        if target.name != "SKILL.md":
            raise FileNotFoundError(f"{target} is not a SKILL.md file")
        return [target]

    if not target.exists():
        raise FileNotFoundError(f"{target} does not exist")

    direct_skill = target / "SKILL.md"
    if direct_skill.exists():
        return [direct_skill]

    return sorted(target.glob("*/SKILL.md"), key=lambda path: str(path).lower())
