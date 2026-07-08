import json
import os
import subprocess
import sys
from pathlib import Path


def write_skill(path: Path, name: str, description: str) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "SKILL.md").write_text(
        f"""---
name: {name}
description: {description}
---

# {name}

Focused workflow.
""",
        encoding="utf-8",
    )


def run_cli(project_root: Path, target: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root / "src")
    return subprocess.run(
        [sys.executable, "-m", "skill_doctor", str(target), *args],
        cwd=project_root,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_cli_returns_success_for_warning_only_findings(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )

    result = run_cli(project_root, tmp_path, "--format", "markdown")

    assert result.returncode == 0
    assert "description-too-broad" in result.stdout
    assert result.stderr == ""


def test_cli_can_fail_on_warning_findings(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )

    result = run_cli(project_root, tmp_path, "--fail-on", "warning")

    assert result.returncode == 1
    assert "description-too-broad" in result.stdout


def test_cli_reads_json_config_file(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )
    config = tmp_path / ".skill-doctor.json"
    config.write_text(
        json.dumps({"format": "json", "fail_on": "warning", "body_line_limit": 120}),
        encoding="utf-8",
    )

    result = run_cli(project_root, tmp_path, "--config", str(config))

    assert result.returncode == 1
    parsed = json.loads(result.stdout)
    assert parsed["findings"][0]["code"] == "description-too-broad"


def test_cli_arguments_override_config_file(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )
    config = tmp_path / ".skill-doctor.json"
    config.write_text(json.dumps({"fail_on": "warning"}), encoding="utf-8")

    result = run_cli(project_root, tmp_path, "--config", str(config), "--fail-on", "error")

    assert result.returncode == 0


def test_cli_returns_usage_error_for_invalid_config(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "focused-review",
        "focused-review",
        "Use when reviewing an Agent Skill for trigger precision and publish readiness.",
    )
    config = tmp_path / ".skill-doctor.json"
    config.write_text("{not json", encoding="utf-8")

    result = run_cli(project_root, tmp_path, "--config", str(config))

    assert result.returncode == 2
    assert "config" in result.stderr.lower()


def test_cli_returns_error_for_invalid_skill_name(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(tmp_path / "bad", "Bad Name", "Too short.")

    result = run_cli(project_root, tmp_path, "--format", "json")

    assert result.returncode == 1
    parsed = json.loads(result.stdout)
    assert any(finding["code"] == "invalid-skill-name" for finding in parsed["findings"])


def test_cli_outputs_github_annotations(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )

    result = run_cli(project_root, tmp_path, "--format", "github")

    assert result.returncode == 0
    assert result.stdout.startswith("::warning file=broad-helper,title=description-too-broad::")


def test_cli_outputs_sarif(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]
    write_skill(
        tmp_path / "broad-helper",
        "broad-helper",
        "Use when doing anything with code, docs, tests, files, bugs, reviews, and projects.",
    )

    result = run_cli(project_root, tmp_path, "--format", "sarif")

    assert result.returncode == 0
    parsed = json.loads(result.stdout)
    assert parsed["version"] == "2.1.0"
    assert parsed["runs"][0]["results"][0]["ruleId"] == "description-too-broad"


def test_cli_returns_usage_error_for_missing_path(tmp_path: Path) -> None:
    project_root = Path(__file__).resolve().parents[1]

    result = run_cli(project_root, tmp_path / "missing")

    assert result.returncode == 2
    assert "does not exist" in result.stderr


def test_module_command_runs_from_repo_without_install() -> None:
    project_root = Path(__file__).resolve().parents[1]

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "skill_doctor",
            "examples/good-skills",
            "--format",
            "json",
        ],
        cwd=project_root,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert json.loads(result.stdout)["skills_scanned"] == 1
