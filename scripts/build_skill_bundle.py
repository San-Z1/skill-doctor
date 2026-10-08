"""Build a self-contained Skill archive using the same source as the CLI."""

import argparse
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path, nargs="?", default=Path("dist/skill-doctor-skill.zip"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        skill = root / "skills" / "skill-doctor"
        for path in sorted(skill.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, "skill-doctor/" + path.relative_to(skill).as_posix())
        package = root / "src" / "skill_doctor"
        for path in sorted(package.glob("*.py")):
            archive.write(path, "skill-doctor/scripts/lib/skill_doctor/" + path.name)
        archive.write(root / "LICENSE", "skill-doctor/LICENSE")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
