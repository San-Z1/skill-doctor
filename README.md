# Skill Doctor

[![CI](https://github.com/San-Z1/skill-doctor/actions/workflows/ci.yml/badge.svg)](https://github.com/San-Z1/skill-doctor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-quality%20gate-blue.svg)](skills/skill-doctor)

**The CI quality gate for Agent Skills.**

Review what an Agent Skill pull request changes, not just whether its files look valid. Skill Doctor compares triggers, tool restrictions, instructions, scripts, references, and assets against a Git baseline, with explainable risk levels and a CI gate.

```bash
skill-doctor diff skills --base-ref main --fail-on-risk high
```

Example change evidence:

```text
review-api: modified / HIGH
Tools added: Write
Script added: scripts/check.py
Quality: 100 (A+) -> 100 (A+)
```

A perfect static score can still accompany a behavior-expanding change. No API keys, model calls, or execution of scanned scripts. Risk levels are review heuristics, not a malware or prompt-injection verdict.

[Marketplace](https://github.com/marketplace/actions/skill-doctor-quality-gate) | [Change review guide](docs/change-review.md) | [Standalone Skill ZIP](https://github.com/San-Z1/skill-doctor/releases/download/v1.1.0/skill-doctor-skill.zip)

## 60-Second CI Setup

```yaml
name: Skill Doctor

on:
  pull_request:
  push:
    branches: [main]

jobs:
  skill-doctor:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: San-Z1/skill-doctor@v1
        with:
          path: skills
          fail-on: warning
          fail-on-risk: high
```

Local check:

```bash
python -m pip install -e .
skill-doctor skills --format markdown --fail-on warning
```

On pull requests, the Action compares against the PR base commit automatically, fetching that commit if needed. On pushes, it only scans unless `compare-ref` is supplied. It adds workflow annotations and a job summary without write permissions or PR comments.

Install the CLI directly from a release:

```bash
python -m pip install "git+https://github.com/San-Z1/skill-doctor.git@v1.1.0"
```

Install the source Agent Skill with a GitHub CLI version that supports Skill installation (the CLI package above is required outside a cloned repository):

```bash
gh skill install San-Z1/skill-doctor skill-doctor@v1
```

Typical output:

```markdown
# Skill Doctor Report

- Root: `.../skills`
- Skills scanned: 4
- Findings: 7
- Quality score: 18/100 (F)

## ERROR: `invalid-skill-name`

- Path: `bad-name`
- Message: Skill name `Bad Name` is not lowercase kebab-case.
- Suggestion: Rename the skill with lowercase letters, digits, and hyphens only.
```

## Why It Exists

Agent Skills are easy to write and easy to break. Skill Doctor gives maintainers a deterministic review layer before a skill is shared, installed, or accepted in a pull request.

It helps authors catch:

- vague or overly broad trigger descriptions,
- skill names and folders that do not line up,
- bloated `SKILL.md` files that should use progressive disclosure,
- resource files that agents cannot discover from the main skill instructions,
- resource references that point at missing files,
- sibling skills that compete for the same trigger,
- wildcard `allowed-tools` hints.

It is intentionally not a malware scanner. Skill Doctor is the publishing and maintainability check you run before sharing a skill on GitHub or installing a new skill collection.

## Quick Start

Run from a cloned repository:

```bash
python -m skill_doctor examples/problematic-skills --format markdown
```

Or install it in editable mode:

```bash
python -m pip install -e .
skill-doctor examples/problematic-skills --format markdown
```

For automation:

```bash
skill-doctor examples/good-skills --format json
```

Fail CI on warnings instead of errors only:

```bash
skill-doctor skills --fail-on warning
```

Emit GitHub Actions annotations:

```bash
skill-doctor skills --format github --fail-on warning
```

Emit SARIF for GitHub code scanning or other SARIF consumers:

```bash
skill-doctor skills --format sarif
```

Use a JSON config file:

```bash
skill-doctor skills --config examples/skill-doctor.config.json
```

Supported config keys:

```json
{
  "format": "github",
  "fail_on": "warning",
  "body_line_limit": 180
}
```

Exit codes:

- `0`: scan completed with no `error` findings,
- `1`: scan completed and found at least one finding at or above the `--fail-on` threshold,
- `2`: CLI usage, filesystem, or parsing failure.

## Example Output

```markdown
# Skill Doctor Report

- Root: `.../examples/problematic-skills`
- Skills scanned: 4
- Findings: 7
- Quality score: 18/100 (F)

## ERROR: `invalid-skill-name`

- Path: `bad-name`
- Message: Skill name `Bad Name` is not lowercase kebab-case.
- Suggestion: Rename the skill with lowercase letters, digits, and hyphens only.
```

## What It Checks

| Code | Severity | Meaning |
|---|---:|---|
| `missing-name` | error | `SKILL.md` has no `name` field. |
| `invalid-skill-name` | error | The skill name is not lowercase kebab-case. |
| `missing-description` | error | `SKILL.md` has no `description` field. |
| `folder-name-mismatch` | warning | Folder name and skill name differ. |
| `missing-trigger-context` | warning | Description does not clearly say when to use the skill. |
| `description-too-broad` | warning | Description is likely to trigger for unrelated tasks. |
| `body-too-large` | warning | `SKILL.md` should probably move detail into `references/`. |
| `allowed-tools-too-broad` | warning | `allowed-tools` uses a wildcard. |
| `overlapping-description` | warning | Sibling skill descriptions are too similar. |
| `missing-resource` | warning | `SKILL.md` references a missing `scripts/`, `references/`, or `assets/` file. |
| `orphan-resource` | info | A resource file is not mentioned from `SKILL.md`. |

## Use As An Agent Skill

This repository also ships a `skill-doctor` Agent Skill:

```text
skills/skill-doctor/
```

An agent can invoke the bundled wrapper:

```bash
python skills/skill-doctor/scripts/run_skill_doctor.py <target> --format markdown
```

The wrapper loads the local Python package from `src/`, so it works inside a cloned repository without installing the package first.

For a standalone installation or a Skill marketplace upload, use `skill-doctor-skill.zip` from [Releases](https://github.com/San-Z1/skill-doctor/releases). It includes `SKILL.md`, references, the wrapper, and the runtime. Unzip the archive into your agent's Skill installation directory, and invoke the wrapper using its actual installed path. Python 3.10+ is required; diff mode also needs Git.

Do not upload GitHub's whole-repository source ZIP as a single Skill package. To build the dedicated archive locally:

```bash
python scripts/build_skill_bundle.py
```

## Upload To GitHub

See [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md) for the shortest web-upload and git-push paths.

## Distribution

- [GitHub Actions Marketplace launch checklist](docs/distribution/marketplace.md)
- [Launch post draft](docs/distribution/launch-post.md)
- Demo recording helper: `./scripts/record-demo.ps1`

## Development

Release notes are in [CHANGELOG.md](CHANGELOG.md), with the latest release draft at [docs/releases/v1.1.0.md](docs/releases/v1.1.0.md).

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Build a local wheel:

```bash
python -m pip wheel . --no-deps -w dist
```

Run the full local release verification:

```powershell
./scripts/verify-release.ps1
```

Run the demo checks:

```bash
python -m skill_doctor examples/good-skills --format json
python -m skill_doctor examples/problematic-skills --format markdown
python -m skill_doctor examples/problematic-skills --format github
python -m skill_doctor examples/problematic-skills --format sarif
python -m skill_doctor examples/problematic-skills --config examples/skill-doctor.config.json
```

Prepare and push the first GitHub release after configuring your Git identity and creating an empty GitHub repository:

```powershell
./scripts/publish-github.ps1 -RemoteUrl "https://github.com/your-github-user/skill-doctor.git"
```

## Design Notes

Skill Doctor is static by design. It reads `SKILL.md` files and resource paths, but it does not execute scripts inside the scanned skill. This keeps reviews safe enough to run on unfamiliar skill repositories.

Change review includes uncommitted workspace changes. It does not modify the branch, index, or working tree. Duplicate Skill names and symlink resources fail comparison explicitly. The lightweight frontmatter reader expects scalar `key: value` fields; full YAML block scalars and multiline lists are not supported. See [limitations and risk rules](docs/change-review.md).

## License

MIT
