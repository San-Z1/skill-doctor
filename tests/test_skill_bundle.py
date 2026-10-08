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
