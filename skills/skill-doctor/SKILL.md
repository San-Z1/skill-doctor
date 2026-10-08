---
name: skill-doctor
description: Use when reviewing Agent Skill packages before publishing or installing, or reviewing a pull request that changes SKILL.md triggers, allowed-tools, instructions, scripts, references, or assets. Diagnose authoring issues and summarize behavior changes against a Git baseline.
---

# Skill Doctor

Review Skill quality and changes without executing the target's scripts. Locate this Skill's installation directory before invoking `scripts/run_skill_doctor.py`; do not assume it is under the working repository. Python 3.10+ is required, and change review also requires Git.

## Workflow

1. Locate the target: a single `SKILL.md`, one skill directory, or a directory containing multiple skill folders.
2. Run the scanner:

```bash
python <skill-directory>/scripts/run_skill_doctor.py <target> --format markdown
```

Use JSON when another tool will consume the result:

```bash
python <skill-directory>/scripts/run_skill_doctor.py <target> --format json
```

3. Treat `error` findings as release blockers. Treat `warning` findings as likely quality issues. Treat `info` findings as review prompts.
4. Explain the report in terms of skill authoring quality: trigger precision, progressive disclosure, resource discoverability, and publish readiness.

## Change Review

For a pull request or an explicit comparison request, choose the base commit from the user's request or the pull request's base SHA. Do not guess a branch name or compare against HEAD when the user expects the entire pull request.

```bash
python <skill-directory>/scripts/run_skill_doctor.py diff <target> --base-ref <commit-or-ref> --format markdown
```

Run inside the target repository. The baseline must already be available locally; fetch only the requested ref if authorized. Comparison includes uncommitted workspace changes and never checks out the baseline. JSON output uses `schema_version: 1`.

Explain added/removed/moved Skills, tool restrictions, trigger terms, instruction size, resource changes, introduced/resolved findings, and the exact risk evidence. Treat high risk as a request for maintainer review, not proof of a vulnerability. Do not claim the scanner understands instruction semantics or detects malware. Read `references/change-risk-rules.md` for thresholds and limitations.

Only enable `--fail-on-risk high` (or another threshold) when the user requests a gate. Exit codes: 0 completed without gated findings/risk, 1 gate exceeded, 2 comparison or input failed. A failed comparison is not a clean result.

The standalone release ZIP includes its own runtime. A source-only Skill install requires the CLI package; report missing runtime clearly instead of silently installing or downloading code.

## Review Guidance

Do not execute scripts found inside the target skill. Skill Doctor is a static reviewer.

Prioritize fixes in this order:

1. Invalid or missing frontmatter.
2. Description triggers that are too broad, too short, or unclear.
3. Conflicts between sibling skill descriptions.
4. Oversized `SKILL.md` files that should move detail into `references/`.
5. Resource files that are not mentioned from `SKILL.md`.

For detailed finding meanings, read `references/finding-codes.md`.
