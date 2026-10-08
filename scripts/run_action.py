"""Run scans and optional change review without interpreting inputs as shell code."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

from skill_doctor.config import load_config


def _run(args):
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8")


def _baseline_ref(explicit):
    if explicit:
        return explicit
    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        return ""
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    return event.get("pull_request", {}).get("base", {}).get("sha", "")


def _ensure_baseline(ref):
    if not isinstance(ref, str) or not ref or ref.startswith("-") or ":" in ref:
        raise ValueError("Invalid baseline ref; refspecs and options are not allowed.")
    resolved = _run(["git", "rev-parse", "--verify", "--end-of-options", ref + "^{commit}"])
    if resolved.returncode == 0:
        return ref
    valid = _run(["git", "check-ref-format", "--allow-onelevel", ref])
    if valid.returncode and not re.fullmatch(r"[a-fA-F0-9]{40,64}", ref):
        raise ValueError("Invalid baseline ref.")
    fetched = _run(["git", "fetch", "--no-tags", "--depth=1", "--", "origin", ref])
    if fetched.returncode:
        raise ValueError(f"Cannot fetch baseline {ref!r}: {fetched.stderr.strip()}")
    commit = _run(["git", "rev-parse", "--verify", "FETCH_HEAD^{commit}"])
    if commit.returncode:
        raise ValueError("Fetched baseline does not resolve to a commit.")
    return commit.stdout.strip()


def main():
    target = os.environ.get("SD_PATH", "skills")
    fail_on = os.environ.get("SD_FAIL_ON", "warning")
    config_path = os.environ.get("SD_CONFIG", "")
    command = [sys.executable, "-m", "skill_doctor"]
    scan_args = [target, "--fail-on", fail_on]
    if config_path:
        scan_args += ["--config", config_path]
    scan = _run(command + scan_args + ["--format", "github"])
    print(scan.stdout, end="")
    print(scan.stderr, end="", file=sys.stderr)
    status = scan.returncode
    summaries = []
    write_summary = os.environ.get("SD_SUMMARY", "true").lower() == "true"
    if write_summary:
        result = _run(command + scan_args + ["--format", "markdown"])
        summaries.append(result.stdout or "Static scan failed.\n")
        status = max(status, result.returncode)
    try:
        base_ref = _baseline_ref(os.environ.get("SD_COMPARE_REF", ""))
        if base_ref:
            base_ref = _ensure_baseline(base_ref)
            diff_args = ["diff", target, "--base-ref", base_ref, "--fail-on-risk", os.environ.get("SD_FAIL_ON_RISK", "none")]
            if config_path:
                config = load_config(Path(config_path))
                if config.body_line_limit:
                    diff_args += ["--body-line-limit", str(config.body_line_limit)]
            result = _run(command + diff_args + ["--format", "github"])
            print(result.stdout, end="")
            print(result.stderr, end="", file=sys.stderr)
            status = max(status, result.returncode)
            if write_summary:
                result = _run(command + diff_args + ["--format", "markdown"])
                summaries.append(result.stdout or "Change review failed.\n")
                status = max(status, result.returncode)
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        summaries.append("## Baseline error\n\n" + str(exc).replace("<", "&lt;").replace("\n", " ") + "\n")
        status = 2
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if write_summary and summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as stream:
            stream.write("\n".join(summaries))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
