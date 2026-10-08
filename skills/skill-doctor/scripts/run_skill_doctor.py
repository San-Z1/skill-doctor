from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    script = Path(__file__).resolve()
    bundled = script.parent / "lib"
    # Release archives carry the runtime; source installs use the repository or installed package.
    if (bundled / "skill_doctor" / "cli.py").is_file():
        sys.path.insert(0, str(bundled))
    elif len(script.parents) > 3:
        src = script.parents[3] / "src"
        if (src / "skill_doctor" / "cli.py").is_file():
            sys.path.insert(0, str(src))
    try:
        from skill_doctor.cli import main as cli_main
    except ModuleNotFoundError as exc:
        if exc.name != "skill_doctor":
            raise
        print("Skill Doctor runtime is missing. Use the standalone Skill ZIP from the GitHub release, "
              "or install the CLI package before running this source Skill.", file=sys.stderr)
        return 2

    return cli_main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(main())
