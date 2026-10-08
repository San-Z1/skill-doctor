"""Show a real change review in an isolated throwaway repository."""

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from skill_doctor.cli import main as cli_main


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", choices=("markdown", "json", "github"), default="markdown")
    parser.add_argument("--fail-on-risk", default="none", choices=("none", "low", "medium", "high"))
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="skill-doctor-demo-") as temporary:
        root = Path(temporary)
        skill = root / "skills" / "review-api"
        skill.mkdir(parents=True)
        source = skill / "SKILL.md"
        source.write_text("---\nname: review-api\ndescription: Use when reviewing API changes for compatibility risks.\n"
                          "allowed-tools: Read\n---\n# Review API\nInspect changes.\n", encoding="utf-8")
        for command in (["init", "-b", "main"], ["config", "user.name", "Skill Doctor Demo"],
                        ["config", "user.email", "demo@example.test"], ["add", "."], ["commit", "-m", "baseline"]):
            subprocess.run(["git", "-C", str(root), *command], check=True, capture_output=True)
        source.write_text(source.read_text(encoding="utf-8").replace("Read\n", "Read, Write\n")
                          + "Review scripts/check.py before use.\n", encoding="utf-8")
        (skill / "scripts").mkdir()
        (skill / "scripts" / "check.py").write_text("raise RuntimeError('This example script must not be executed')\n", encoding="utf-8")
        return cli_main(["diff", str(root / "skills"), "--base-ref", "main", "--format", args.format,
                         "--fail-on-risk", args.fail_on_risk])


if __name__ == "__main__":
    raise SystemExit(main())
