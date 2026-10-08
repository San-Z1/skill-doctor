import hashlib
from pathlib import Path

import pytest

from skill_doctor.change_models import risk_at_least
from skill_doctor.snapshot import snapshot_target


def write_skill(root: Path, *, tools: str = "Read, Grep", body: str = "Read references/check.md.") -> Path:
    skill = root / "review-api"
    (skill / "references").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: review-api\n"
        "description: Use when reviewing API changes for compatibility risks.\n"
        f"allowed-tools: {tools}\n---\n\n# Review API\n\n{body}\n",
        encoding="utf-8",
    )
    (skill / "references" / "check.md").write_bytes(b"# Checklist\n")
    return skill


def test_snapshot_normalizes_and_hashes_without_execution(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    result = snapshot_target(tmp_path)
    snapshot = result.skills[0]
    assert result.score == 100
    assert snapshot.relative_path == "review-api"
    assert snapshot.trigger_terms == ("api", "changes", "compatibility", "reviewing", "risks")
    assert snapshot.allowed_tools == ("Grep", "Read")
    assert snapshot.resources[0].path == "references/check.md"
    assert snapshot.resources[0].sha256 == hashlib.sha256(b"# Checklist\n").hexdigest()
    assert snapshot.body_nonempty_lines == 2
    assert len(snapshot.body_sha256) == 64
    assert (skill / "references" / "check.md").read_bytes() == b"# Checklist\n"


def test_single_file_and_single_directory_use_same_relative_identity(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    assert snapshot_target(skill) == snapshot_target(skill / "SKILL.md")
    assert snapshot_target(skill).skills[0].relative_path == "."


def test_same_size_body_change_changes_hash(tmp_path: Path) -> None:
    skill = write_skill(tmp_path, body="Keep references/check.md.")
    before = snapshot_target(skill).skills[0]
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    (skill / "SKILL.md").write_text(text.replace("Keep", "Drop"), encoding="utf-8")
    after = snapshot_target(skill).skills[0]
    assert before.body_word_count == after.body_word_count
    assert before.body_nonempty_lines == after.body_nonempty_lines
    assert before.body_sha256 != after.body_sha256


def test_tool_arguments_preserve_spaces_and_commas_inside_parentheses(tmp_path: Path) -> None:
    write_skill(tmp_path, tools='Read Bash(git log:*) Bash(echo a,b)')
    tools = snapshot_target(tmp_path).skills[0].allowed_tools
    assert tools == ("Bash(echo a,b)", "Bash(git log:*)", "Read")


def test_duplicate_names_are_not_silently_discarded(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    duplicate = tmp_path / "duplicate"
    duplicate.mkdir()
    (duplicate / "SKILL.md").write_bytes((skill / "SKILL.md").read_bytes())
    with pytest.raises(ValueError, match="Duplicate skill name"):
        snapshot_target(tmp_path)


def test_generated_python_cache_is_not_a_skill_resource(tmp_path: Path) -> None:
    skill = write_skill(tmp_path)
    before = snapshot_target(tmp_path)
    cache = skill / "scripts" / "__pycache__"
    cache.mkdir(parents=True)
    (cache / "helper.cpython-310.pyc").write_bytes(b"generated")
    assert snapshot_target(tmp_path) == before


@pytest.mark.parametrize("content,canonical", [
    (b"hello\r\nworld\r\n", b"hello\nworld\n"),
    (b"binary\0\r\n", b"binary\0\r\n"),
    (b"\xff\r\n", b"\xff\r\n"),
    (b"a" * 65535 + b"\r\n", b"a" * 65535 + b"\n"),
], ids=("utf8-text", "binary-nul", "binary-invalid-utf8", "chunk-boundary"))
def test_resource_hash_normalizes_text_but_preserves_binary(tmp_path, content, canonical):
    skill = write_skill(tmp_path)
    (skill / "references" / "check.md").write_bytes(content)
    resource = snapshot_target(tmp_path).skills[0].resources[0]
    assert resource.sha256 == hashlib.sha256(canonical).hexdigest()


@pytest.mark.parametrize("actual,threshold,expected", [
    ("high", "high", True), ("medium", "high", False),
    ("high", "none", False), ("none", "low", False), ("low", "low", True),
])
def test_risk_threshold(actual: str, threshold: str, expected: bool) -> None:
    assert risk_at_least(actual, threshold) is expected
