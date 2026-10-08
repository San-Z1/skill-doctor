"""Build a self-contained Skill archive using the same source as the CLI."""

import argparse
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, nargs="?", default=Path("dist/skill-doctor-skill.zip"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    package_files = sorted((root / "src" / "skill_doctor").glob("*.py"))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        skill = root / "skills" / "skill-doctor"
        for path in sorted(skill.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                name = "skill-doctor/" + path.relative_to(skill).as_posix()
                if path == skill / "SKILL.md":
                    manifest = "\n## Bundled Runtime\n\nThe wrapper imports these support modules; do not invoke them independently:\n\n"
                    manifest += "\n".join("- `scripts/lib/skill_doctor/" + module.name + "`" for module in package_files) + "\n"
                    archive.writestr(name, path.read_text(encoding="utf-8") + manifest)
                else:
                    archive.write(path, name)
        for path in package_files:
            archive.write(path, "skill-doctor/scripts/lib/skill_doctor/" + path.name)
        archive.write(root / "LICENSE", "skill-doctor/LICENSE")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
