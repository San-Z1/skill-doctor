# Skill Doctor

Skill Doctor is a quality diagnostic tool for Agent Skills. It helps authors catch the problems that make skills hard for AI agents and other `SKILL.md`-compatible tools to use well:

- vague or overly broad trigger descriptions,
- skill names and folders that do not line up,
- bloated `SKILL.md` files that should use progressive disclosure,
- resource files that agents cannot discover from the main skill instructions,
- sibling skills that compete for the same trigger,
- wildcard `allowed-tools` hints.

It is intentionally not a malware scanner. Skill Doctor is the publishing and maintainability check you run before sharing a skill on GitHub or installing a new skill collection.

## Quick Start

Run from this repository:

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

## Upload To GitHub

See [GITHUB_UPLOAD.md](GITHUB_UPLOAD.md) for the shortest web-upload and git-push paths.

## Development

Release notes start in [CHANGELOG.md](CHANGELOG.md), with the first GitHub release draft at [docs/releases/v0.1.0.md](docs/releases/v0.1.0.md).

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

## License

MIT
