# Release Checklist

Use this checklist before publishing a new Skill Doctor release.

## Before Release

Recommended local verification:

```powershell
./scripts/verify-release.ps1
```

Manual checks:

- Run `python -m pytest -q`.
- Run `python -m pip wheel . --no-deps -w dist`.
- Run `python -m skill_doctor examples/good-skills --format json`.
- Run `python -m skill_doctor examples/problematic-skills --format markdown` and confirm it exits with `1`.
- Run `python -m skill_doctor examples/problematic-skills --format github` and confirm it emits GitHub Actions annotations.
- Run `python -m skill_doctor examples/problematic-skills --format sarif` and confirm it emits SARIF 2.1.0 JSON.
- Confirm Markdown, JSON, and SARIF outputs include the quality score and grade.
- Run `python -m skill_doctor examples/problematic-skills --config examples/skill-doctor.config.json` and confirm config loading works.
- Run `python -m skill_doctor skills --fail-on warning` and confirm it exits with `0`.
- Run a placeholder scan for common unfinished markers and confirm any matches are intentional.
- Run a public file scan for platform/vendor names and confirm any matches are intentional.
- Confirm `docs/distribution/marketplace.md`, `docs/distribution/launch-post.md`, and `scripts/record-demo.ps1` are current.
- Run `./scripts/make-release-zip.ps1` if you want a clean upload archive.

## GitHub Setup

- Create a public repository named `skill-doctor`.
- Add a CI badge to the README after the public GitHub repository exists.
- Configure repository topics: `agent-skills`, `skill-quality`, `ai-agents`, `lint`, `sarif`, `github-actions`.
- Enable GitHub Actions.
- Enable private vulnerability reporting if available.
- Publish a release tag before promoting the `uses: San-Z1/skill-doctor@v1` workflow snippet.

## First Push

Recommended PowerShell helper:

```powershell
./scripts/publish-github.ps1 -RemoteUrl "https://github.com/your-github-user/skill-doctor.git"
```

Manual commands:

```bash
git config user.name "Your Name"
git config user.email "you@example.com"
git commit -m "Initial Skill Doctor project"
git branch -M main
git remote add origin https://github.com/your-github-user/skill-doctor.git
git push -u origin main
```
