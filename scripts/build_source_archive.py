"""Create a source archive with relative paths and no local build artifacts."""

import argparse
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    ignored = {".git", ".pytest_cache", "dist", "build", "__pycache__", ".venv", "venv"}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if any(part in ignored or part.endswith(".egg-info") for part in relative.parts):
                continue
            if path.is_file() and not path.is_symlink() and path.suffix != ".pyc" and path.resolve() != output:
                archive.write(path, relative.as_posix())
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
