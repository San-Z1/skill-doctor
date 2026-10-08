import subprocess
from pathlib import Path

import pytest

from skill_doctor.git_baseline import GitBaselineError, baseline_target, safe_destination, review_target


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


def test_committed_crlf_script_is_not_a_false_modification(repository):
    skill = repository / "skills" / "review-api"
    (skill / "scripts").mkdir()
    (skill / "scripts" / "check.py").write_bytes(b"# committed text\r\npass\r\n")
    (repository / ".gitattributes").write_text("*.py text eol=crlf\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "text resource")
    assert review_target(repository / "skills", "HEAD").overall_risk == "none"


def test_export_ignore_cannot_hide_baseline_resource_deletion(repository):
    skill = repository / "skills" / "review-api"
    (skill / "scripts").mkdir()
    resource = skill / "scripts" / "check.py"
    resource.write_bytes(b"pass\n")
    (repository / ".gitattributes").write_text("skills/review-api/scripts/* export-ignore\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "export attributes")
    resource.unlink()
    report = review_target(repository / "skills", "HEAD")
    assert report.overall_risk == "medium"
    assert report.changes[0].resources_removed[0].path == "scripts/check.py"


def test_export_subst_does_not_change_baseline_content(repository):
    skill = repository / "skills" / "review-api"
    (skill / "references").mkdir()
    (skill / "references" / "hash.md").write_bytes(b"$Format:%H$\n")
    (repository / ".gitattributes").write_text("*.md export-subst\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "export substitution")
    assert review_target(repository / "skills", "HEAD").overall_risk == "none"


@pytest.mark.parametrize("encoding,git_encoding", [("utf-16", "UTF-16"), ("utf-16-le", "UTF-16LE")])
def test_working_tree_encoding_does_not_create_false_script_changes(repository, encoding, git_encoding):
    skill = repository / "skills" / "review-api"
    (skill / "scripts").mkdir()
    (skill / "scripts" / "check.ps1").write_bytes("Write-Output 'check'\r\n".encode(encoding))
    (repository / ".gitattributes").write_text("*.ps1 text working-tree-encoding=" + git_encoding + "\n", encoding="utf-8")
    git(repository, "add", ".")
    git(repository, "commit", "-m", "encoded resource")
    assert git(repository, "status", "--porcelain") == b""
    assert review_target(repository / "skills", "HEAD").overall_risk == "none"


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


@pytest.mark.parametrize("name", ["../escape", "/escape", "C:/escape", "a\\escape", "", "a\0b"])
def test_unsafe_baseline_paths_are_rejected(tmp_path, name):
    with pytest.raises(GitBaselineError, match="Unsafe"):
        safe_destination(name, tmp_path)


def test_git_symlink_entry_is_rejected_without_checkout(repository):
    result = subprocess.run(["git", "-C", str(repository), "hash-object", "-w", "--stdin"], input=b"outside", capture_output=True, check=True)
    sha = result.stdout.decode().strip()
    git(repository, "update-index", "--add", "--cacheinfo", "120000," + sha + ",skills/review-api/references/link")
    git(repository, "commit", "-m", "symlink entry")
    with pytest.raises(GitBaselineError, match="Unsafe"):
        review_target(repository / "skills", "HEAD")
