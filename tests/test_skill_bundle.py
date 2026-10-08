import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_standalone_bundle_runs_scan_and_diff_help(tmp_path):
    archive = tmp_path / "skill.zip"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_skill_bundle.py"), str(archive)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(archive) as package:
        assert all("__pycache__" not in name and not name.endswith(".pyc") for name in package.namelist())
        package.extractall(tmp_path / "unpacked")
    runner = tmp_path / "unpacked" / "skill-doctor" / "scripts" / "run_skill_doctor.py"
    result = subprocess.run([sys.executable, "-I", str(runner), str(ROOT / "examples" / "good-skills"), "--format", "json"], capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert '"score": 100' in result.stdout
    result = subprocess.run([sys.executable, "-I", str(runner), "diff", "--help"], capture_output=True, text=True, cwd=tmp_path)
    assert result.returncode == 0
    assert "--fail-on-risk" in result.stdout


def test_missing_runtime_has_actionable_error_not_traceback(tmp_path):
    runner = tmp_path / "scripts" / "run_skill_doctor.py"
    runner.parent.mkdir()
    shutil.copyfile(ROOT / "skills" / "skill-doctor" / "scripts" / runner.name, runner)
    result = subprocess.run([sys.executable, "-I", "-S", str(runner), "--help"], capture_output=True, text=True)
    assert result.returncode == 2
    assert "standalone Skill ZIP" in result.stderr
    assert "Traceback" not in result.stderr


def test_source_release_preserves_directory_structure(tmp_path):
    archive = tmp_path / "source.zip"
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_source_archive.py"), str(archive)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    with zipfile.ZipFile(archive) as package:
        assert "src/skill_doctor/cli.py" in package.namelist()
        assert "skills/skill-doctor/SKILL.md" in package.namelist()
        assert "action.yml" in package.namelist()
        assert not any("__pycache__" in name or name.startswith(".git/") for name in package.namelist())


def test_change_demo_produces_real_gated_report():
    import json
    result = subprocess.run([sys.executable, str(ROOT / "scripts" / "demo_change_review.py"), "--format", "json", "--fail-on-risk", "high"], capture_output=True, text=True)
    assert result.returncode == 1, result.stderr
    report = json.loads(result.stdout)
    assert report["overall_risk"] == "high"
    assert report["changes"][0]["tools_added"] == ["Write"]
    assert report["changes"][0]["resources_added"][0]["path"] == "scripts/check.py"


def test_release_verifier_stops_when_tests_fail():
    import pytest
    shell = shutil.which("powershell") or shutil.which("pwsh")
    if shell is None:
        pytest.skip("PowerShell is unavailable")
    script = str(ROOT / "scripts" / "verify-release.ps1").replace("'", "''")
    command = "function python { $global:LASTEXITCODE = 7 }; & '" + script + "'"
    result = subprocess.run([shell, "-NoProfile", "-Command", command], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode != 0
    assert "Run tests failed with exit code 7" in result.stderr
    assert "Build wheel" not in result.stdout
