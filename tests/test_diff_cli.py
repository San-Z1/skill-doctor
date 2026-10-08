import json

import pytest

from skill_doctor.cli import main
from test_git_baseline import git, repository


def test_diff_cli_json_and_no_changes(repository, capsys):
    assert main(["diff", "--base-ref", "HEAD", str(repository / "skills"), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["overall_risk"] == "none"


@pytest.mark.parametrize("threshold,exit_code", [("none", 0), ("low", 1), ("medium", 1), ("high", 1)])
def test_diff_cli_risk_gating(repository, capsys, threshold, exit_code):
    skill = repository / "skills" / "review-api" / "SKILL.md"
    skill.write_text(skill.read_text().replace("Read", "Read, Write"), encoding="utf-8")
    assert main(["diff", str(repository / "skills"), "--base-ref", "HEAD", "--fail-on-risk", threshold]) == exit_code
    assert "HIGH" in capsys.readouterr().out


def test_diff_errors(repository, capsys):
    assert main(["diff", str(repository / "skills"), "--base-ref", "missing"]) == 2
    assert "baseline ref" in capsys.readouterr().err
    assert main(["diff", str(repository / "missing"), "--base-ref", "HEAD"]) == 2


def test_existing_scan_stays_compatible(repository, capsys):
    assert main([str(repository / "skills"), "--format", "json"]) == 0
    assert json.loads(capsys.readouterr().out)["skills_scanned"] == 1


def test_diff_positive_line_limit_and_no_sarif(repository):
    with pytest.raises(SystemExit) as exc:
        main(["diff", str(repository / "skills"), "--base-ref", "HEAD", "--body-line-limit", "0"])
    assert exc.value.code == 2
    with pytest.raises(SystemExit):
        main(["diff", str(repository / "skills"), "--base-ref", "HEAD", "--format", "sarif"])
