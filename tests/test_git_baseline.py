import io
import subprocess
import tarfile
from pathlib import Path

import pytest

from skill_doctor.git_baseline import GitBaselineError, baseline_target, extract_archive, review_target


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.name", "Test")
    git(tmp_path, "config", "user.email", "test@example.test")
    skill = tmp_path / "skills" / "review-api"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\nname: review-api\ndescription: Use when reviewing API changes for compatibility risks.\n"
        "allowed-tools: Read\n---\nInspect API changes.\n", encoding="utf-8",
    )
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "baseline")
    return tmp_path


def test_review_preserves_index_branch_and_dirty_worktree(repository):
    target = repository / "skills"
    source = target / "review-api" / "SKILL.md"
    source.write_text(source.read_text().replace("Read", "Read, Write"), encoding="utf-8")
    git(repository, "add", ".")
    (repository / "untracked.txt").write_text("keep", encoding="utf-8")
    before = git(repository, "status", "--porcelain=v1")
    branch = git(repository, "rev-parse", "HEAD")
    report = review_target(target, "HEAD")
    assert report.overall_risk == "high"
    assert report.changes[0].tools_added == ("Write",)
    assert git(repository, "status", "--porcelain=v1") == before
    assert git(repository, "rev-parse", "HEAD") == branch


def test_baseline_cleanup_on_success_and_exception(repository):
    with baseline_target(repository / "skills", "HEAD") as target:
        temporary = target
        assert (target / "review-api" / "SKILL.md").is_file()
    assert not temporary.exists()
    with pytest.raises(RuntimeError):
        with baseline_target(repository / "skills", "HEAD") as target:
            temporary = target
            raise RuntimeError("test")
    assert not temporary.exists()


def test_baseline_absent_and_removed_skill(repository):
    new = repository / "new-skills"
    new.mkdir()
    assert review_target(new, "HEAD").overall_risk == "none"
    source = repository / "skills" / "review-api" / "SKILL.md"
    source.unlink()
    assert review_target(repository / "skills", "HEAD").summary.skills_removed == 1


def test_single_skill_file_includes_resources(repository):
    skill = repository / "skills" / "review-api"
    (skill / "scripts").mkdir()
    (skill / "scripts" / "never-run.py").write_text("raise RuntimeError('must not run')", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "resource")
    assert review_target(skill / "SKILL.md", "HEAD").overall_risk == "none"


@pytest.mark.parametrize("ref", ["does-not-exist", "--output=outside", "HEAD:path"])
def test_unknown_or_noncommit_ref(repository, ref):
    with pytest.raises(GitBaselineError, match="baseline ref"):
        review_target(repository / "skills", ref)


def test_non_git_missing_target_and_outside_target(tmp_path_factory, repository):
    non_git = tmp_path_factory.mktemp("non-git")
    with pytest.raises(GitBaselineError, match="Git repository"):
        review_target(non_git, "HEAD")
    with pytest.raises(FileNotFoundError):
        review_target(repository / "missing", "HEAD")


@pytest.mark.parametrize("name,kind", [
    ("../escape", tarfile.REGTYPE), ("/escape", tarfile.REGTYPE),
    ("C:/escape", tarfile.REGTYPE), ("a\\escape", tarfile.REGTYPE),
    ("link", tarfile.SYMTYPE), ("hard", tarfile.LNKTYPE), ("device", tarfile.CHRTYPE),
])
def test_unsafe_archive_entries_are_rejected(tmp_path, name, kind):
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as archive:
        member = tarfile.TarInfo(name)
        member.type = kind
        member.linkname = "outside"
        archive.addfile(member)
    data.seek(0)
    with pytest.raises(GitBaselineError, match="Unsafe"):
        extract_archive(data, tmp_path)
