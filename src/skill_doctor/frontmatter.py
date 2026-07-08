from __future__ import annotations

from pathlib import Path

from .models import SkillDocument


class FrontmatterError(ValueError):
    """Raised when a SKILL.md file has missing or malformed YAML frontmatter."""


def parse_skill_markdown(path: Path) -> SkillDocument:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise FrontmatterError(f"{path} is missing YAML frontmatter")

    end_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_index = index
            break

    if end_index is None:
        raise FrontmatterError(f"{path} has unterminated YAML frontmatter")

    metadata: dict[str, str] = {}
    for index, line in enumerate(lines[1:end_index], start=2):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise FrontmatterError(f"{path} has malformed frontmatter line {index}")
        key, value = stripped.split(":", 1)
        key = key.strip()
        if not key:
            raise FrontmatterError(f"{path} has empty frontmatter key on line {index}")
        metadata[key] = _clean_scalar(value.strip())

    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return SkillDocument(path=path, metadata=metadata, body=body)


def _clean_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
