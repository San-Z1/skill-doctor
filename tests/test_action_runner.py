import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from test_git_baseline import git, repository


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "run_action.py"


def run_action(repository, monkeypatch, **inputs):
    monkeypatch.chdir(repository)
    env = {"SD_PATH": "skills", "SD_FAIL_ON": "warning", "SD_SUMMARY": "true", **inputs}
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    summary = repository / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    import os
    environment = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run([sys.executable, str(SCRIPT)], env=environment, capture_output=True, text=True), summary


def test_action_explicit_ref_summarizes_and_preserves_gate(repository, monkeypatch):
    source = repository / "skills" / "review-api" / "SKILL.md"
    source.write_text(source.read_text().replace("Read", "Read, Write"), encoding="utf-8")
    result, summary = run_action(repository, monkeypatch, SD_COMPARE_REF="HEAD", SD_FAIL_ON_RISK="high")
    assert result.returncode == 1
    assert "Skill change" in result.stdout
    assert "Overall risk: **HIGH**" in summary.read_text()


def test_action_pr_base_sha_default(repository, monkeypatch):
    event = repository / "event.json"
    event.write_text(json.dumps({"pull_request": {"base": {"sha": git(repository, "rev-parse", "HEAD").decode().strip()}}}))
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    result, summary = run_action(repository, monkeypatch)
    assert result.returncode == 0
    assert "No changes" in summary.read_text()


def test_action_scan_only_and_shell_characters_remain_literal(repository, monkeypatch):
    result, summary = run_action(repository, monkeypatch)
    assert result.returncode == 0
    assert "Change Review" not in summary.read_text()
    result, _ = run_action(repository, monkeypatch, SD_PATH="skills; echo injected")
    assert result.returncode == 2
    assert "injected\n" not in result.stdout


def test_action_missing_ref_fetch_failure_is_visible(repository, monkeypatch):
    result, summary = run_action(repository, monkeypatch, SD_COMPARE_REF="missing")
    assert result.returncode == 2
    assert "Cannot fetch baseline" in result.stderr
    assert "Baseline error" in summary.read_text()


def test_action_fetches_only_requested_baseline(repository, monkeypatch):
    remote = repository.parent / (repository.name + "-remote.git")
    git(repository, "clone", "--bare", str(repository), str(remote))
    git(repository, "remote", "add", "origin", str(remote))
    # The ref exists only at the remote, so the Action must fetch it.
    git(remote, "branch", "release")
    result, summary = run_action(repository, monkeypatch, SD_COMPARE_REF="release")
    assert result.returncode == 0, result.stderr
    assert "No changes" in summary.read_text()
    assert git(repository, "branch", "--show-current").decode().strip() == "main"


def test_action_refspec_cannot_update_local_branch(repository, monkeypatch):
    result, _ = run_action(repository, monkeypatch, SD_COMPARE_REF="main:other")
    assert result.returncode == 2
    assert b"other" not in git(repository, "branch", "--list")
