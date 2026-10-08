from __future__ import annotations

import shutil
import subprocess
import tarfile
import tempfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from .change_review import compare_snapshots
from .snapshot import snapshot_target


class GitBaselineError(ValueError):
    pass


def _git(repository: Path, *args: str) -> bytes:
    result = subprocess.run(["git", "-C", str(repository), *args], capture_output=True)
    if result.returncode:
        detail = result.stderr.decode("utf-8", errors="replace").strip()
        raise GitBaselineError(detail or "Git read failed.")
    return result.stdout


def extract_archive(stream, destination: Path) -> None:
    with tarfile.open(fileobj=stream, mode="r:") as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if (path.is_absolute() or ".." in path.parts or "\\" in member.name
                    or ":" in member.name or not (member.isfile() or member.isdir())):
                raise GitBaselineError(f"Unsafe baseline archive entry: {member.name}")
            target = destination.joinpath(*path.parts)
            if not target.resolve().is_relative_to(destination.resolve()):
                raise GitBaselineError(f"Unsafe baseline archive path: {member.name}")
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)


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
    exists = not path_args or bool(_git(repository, "ls-tree", "-z", commit, *path_args))
    with tempfile.TemporaryDirectory(prefix="skill-doctor-baseline-") as temporary:
        destination = Path(temporary)
        materialized = destination / relative
        if exists:
            with tempfile.TemporaryFile() as stream:
                result = subprocess.run(
                    ["git", "-C", str(repository), "archive", "--format=tar", commit, *path_args],
                    stdout=stream, stderr=subprocess.PIPE,
                )
                if result.returncode:
                    raise GitBaselineError(result.stderr.decode("utf-8", errors="replace").strip())
                stream.seek(0)
                extract_archive(stream, destination)
        if not materialized.exists():
            # A newly created target has an empty baseline, not a failed comparison.
            materialized = destination / "empty-baseline"
            materialized.mkdir(exist_ok=True)
        yield materialized


def review_target(target: Path, base_ref: str, *, body_line_limit: int = 180):
    with baseline_target(target, base_ref) as baseline:
        before = snapshot_target(baseline, body_line_limit=body_line_limit)
    current = snapshot_target(target, body_line_limit=body_line_limit)
    return compare_snapshots(before, current, base_ref=base_ref, target=target.as_posix())
