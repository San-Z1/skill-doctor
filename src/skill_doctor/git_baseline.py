from __future__ import annotations

import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .change_review import compare_snapshots
from .analyzer import RESOURCE_DIRS, is_generated_resource
from .discovery import discover_skills
from .snapshot import snapshot_target


class GitBaselineError(ValueError):
    pass


def _git(repository: Path, *args: str, input: bytes | None = None) -> bytes:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True, input=input)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitBaselineError(detail or "Git read failed.")
    return result.stdout


def safe_destination(name: str, destination: Path) -> Path:
    path = PurePosixPath(name)
    if (path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name
            or not name or "\0" in name):
        raise GitBaselineError(f"Unsafe baseline path: {name}")
    target = destination.joinpath(*path.parts)
    if not target.resolve().is_relative_to(destination.resolve()):
        raise GitBaselineError(f"Unsafe baseline path: {name}")
    return target


def _materialize(repository: Path, commit: str, path_args: list[str], destination: Path) -> None:
    tree = _git(repository, "ls-tree", "-r", "-z", "--full-tree", commit, *path_args)
    entries = []
    for entry in tree.split(b"\0"):
        if not entry:
            continue
        metadata, name = entry.split(b"\t", 1)
        mode, kind, sha = metadata.split()
        if kind != b"blob" or mode not in {b"100644", b"100755"}:
            raise GitBaselineError(f"Unsafe baseline entry type: {name.decode('utf-8', errors='replace')}")
        entries.append((sha, safe_destination(name.decode("utf-8"), destination)))
    if not entries:
        return
    # Raw blobs bypass export-ignore, export-subst, and executable checkout filters.
    with subprocess.Popen(["git", "-C", str(repository), "cat-file", "--batch"],
                          stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        try:
            for sha, path in entries:
                process.stdin.write(sha + b"\n")
                process.stdin.flush()
                header = process.stdout.readline().split()
                if len(header) != 3 or header[1] != b"blob" or header[0] != sha:
                    raise GitBaselineError("Cannot read baseline blob.")
                remaining = int(header[2])
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("wb") as stream:
                    while remaining:
                        chunk = process.stdout.read(min(65536, remaining))
                        if not chunk:
                            raise GitBaselineError("Incomplete baseline blob.")
                        stream.write(chunk)
                        remaining -= len(chunk)
                if process.stdout.read(1) != b"\n":
                    raise GitBaselineError("Invalid baseline blob framing.")
            process.stdin.close()
            if process.wait() != 0:
                raise GitBaselineError(process.stderr.read().decode("utf-8", errors="replace"))
        except BaseException:
            process.kill()
            raise


@contextmanager
def baseline_target(target: Path, base_ref: str):
    if not target.exists():
        raise FileNotFoundError(f"{target} does not exist")
    if target.is_symlink():
        raise GitBaselineError("Symbolic link targets are not supported.")
    target = target.resolve()
    anchor = target.parent if target.is_file() else target
    try:
        repository = Path(_git(anchor, "rev-parse", "--show-toplevel").decode("utf-8").strip())
    except GitBaselineError as exc:
        raise GitBaselineError("Target must be inside a Git repository.") from exc
    relative = target.relative_to(repository.resolve())
    try:
        commit = _git(repository, "rev-parse", "--verify", "--end-of-options", base_ref + "^{commit}").decode().strip()
    except GitBaselineError as exc:
        raise GitBaselineError(f"Cannot resolve baseline ref {base_ref!r} to a commit.") from exc

    # Include sibling resources when the input is a single SKILL.md file.
    archive_path = relative.parent if target.is_file() else relative
    path_args = ["--", archive_path.as_posix()] if archive_path != Path(".") else []
    with tempfile.TemporaryDirectory(prefix="skill-doctor-baseline-") as temporary:
        destination = Path(temporary) / "tree"
        destination.mkdir()
        materialized = destination / relative
        _materialize(repository, commit, path_args, destination)
        if not materialized.exists():
            # A newly created target has an empty baseline, not a failed comparison.
            materialized = Path(temporary) / "empty-baseline"
            materialized.mkdir(exist_ok=True)
        yield materialized


def review_target(target: Path, base_ref: str, *, body_line_limit: int = 180):
    with baseline_target(target, base_ref) as baseline:
        before = snapshot_target(baseline, body_line_limit=body_line_limit)
    current = snapshot_target(target, body_line_limit=body_line_limit, resource_encodings=_working_tree_encodings(target))
    return compare_snapshots(before, current, base_ref=base_ref, target=target.as_posix())


def _working_tree_encodings(target: Path) -> dict[Path, str]:
    target = target.resolve()
    anchor = target.parent if target.is_file() else target
    repository = Path(_git(anchor, "rev-parse", "--show-toplevel").decode("utf-8").strip()).resolve()
    paths = [path for skill in discover_skills(target) for kind in RESOURCE_DIRS
             for path in (skill.path / kind).rglob("*") if path.is_file() and not is_generated_resource(path)]
    if not paths:
        return {}
    names = [path.relative_to(repository).as_posix() for path in paths]
    output = _git(repository, "check-attr", "-z", "working-tree-encoding", "--stdin",
                  input=("\0".join(names) + "\0").encode("utf-8"))
    fields = output.rstrip(b"\0").split(b"\0")
    encodings = {}
    for index in range(0, len(fields), 3):
        name, _, encoding = (field.decode("utf-8") for field in fields[index:index + 3])
        if encoding not in {"unspecified", "unset"}:
            encodings[repository / name] = encoding
    return encodings
