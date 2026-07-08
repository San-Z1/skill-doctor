# Contributing

Thanks for helping improve Skill Doctor.

## Local Setup

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Development Rules

- Keep checks deterministic and static. Do not execute scripts from scanned skills.
- Add or update tests for each new finding code.
- Keep finding messages concise and suggestions actionable.
- Prefer standard-library Python unless a dependency clearly pays for itself.
- Update `skills/skill-doctor/references/finding-codes.md` and README when adding a finding code.

## Pull Request Checklist

- Tests pass with `python -m pytest -q`.
- Example scans still work.
- New checks have fixtures or focused unit tests.
- User-facing docs mention new finding codes or behavior changes.
