# Changelog

All notable changes to Skill Doctor are documented here.

## 1.1.0 - 2026-10-09

### Added

- `diff --base-ref` for deterministic Skill behavior change review with versioned JSON, Markdown, and workflow annotations.
- Trigger/tool changes, instruction content hashes and counts, resource changes, folder moves, introduced/resolved findings, and score deltas.
- Explainable risk classification and `--fail-on-risk none|low|medium|high` gating.
- PR base SHA comparison and optional `compare-ref` / `fail-on-risk` Action inputs without write permissions.
- Standalone Skill archive with bundled runtime and an isolated reproducible demo.

### Fixed

- Action inputs are passed as arguments, never interpolated into shell commands.
- Job summaries survive failed quality/risk gates; baseline fetch errors are not silently ignored.
- Release checks enforce subprocess exit codes; source ZIPs preserve directory structure.
- Missing runtime in source-only Skill installs produces actionable guidance.

Static scan syntax and output formats remain compatible. Risk review does not execute scanned scripts or classify malware.

## 0.1.0 - Initial Release

### Added

- Static Agent Skill discovery for single `SKILL.md` files, skill directories, and skill collections.
- Frontmatter validation for missing or invalid `name` and `description` fields.
- Skill quality checks for trigger clarity, broad descriptions, folder/name mismatch, oversized `SKILL.md` files, orphaned resources, overlapping skill descriptions, and wildcard `allowed-tools`.
- Missing resource reference checks for `scripts/`, `references/`, and `assets/` paths mentioned from `SKILL.md`.
- Quality score and grade in Markdown, JSON, and SARIF reports.
- Markdown, JSON, GitHub Actions annotation, and SARIF 2.1.0 report formats.
- Composite GitHub Action entrypoint for pull request quality gates.
- Config file support through `--config` with `format`, `fail_on`, and `body_line_limit`.
- CI-friendly exit thresholds through `--fail-on error|warning|info`.
- Packaged Agent Skill under `skills/skill-doctor`.
- Example good and problematic skills for demos and tests.
- GitHub Actions CI, issue templates, PR template, contribution guide, security policy, and release scripts.
