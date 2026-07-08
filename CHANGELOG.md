# Changelog

All notable changes to Skill Doctor are documented here.

## 0.1.0 - Initial Release

### Added

- Static Agent Skill discovery for single `SKILL.md` files, skill directories, and skill collections.
- Frontmatter validation for missing or invalid `name` and `description` fields.
- Skill quality checks for trigger clarity, broad descriptions, folder/name mismatch, oversized `SKILL.md` files, orphaned resources, overlapping skill descriptions, and wildcard `allowed-tools`.
- Missing resource reference checks for `scripts/`, `references/`, and `assets/` paths mentioned from `SKILL.md`.
- Markdown, JSON, GitHub Actions annotation, and SARIF 2.1.0 report formats.
- Config file support through `--config` with `format`, `fail_on`, and `body_line_limit`.
- CI-friendly exit thresholds through `--fail-on error|warning|info`.
- Packaged Agent Skill under `skills/skill-doctor`.
- Example good and problematic skills for demos and tests.
- GitHub Actions CI, issue templates, PR template, contribution guide, security policy, and release scripts.
