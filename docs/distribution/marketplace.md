# GitHub Actions Marketplace Launch Checklist

Use this checklist when publishing Skill Doctor as a GitHub Action and preparing the repository for discovery.

## Repository Setup

- Keep `action.yml` in the repository root.
- Keep the `v1` tag updated to the latest stable action commit.
- Use a short About description:

```text
CI quality gates and explainable pull request change review for Agent Skills.
```

- Add repository topics:

```text
agent-skills
skill-quality
github-actions
quality-gate
ai-agents
linter
sarif
ci
```

## Marketplace Copy

Marketplace listing name:

```text
Skill Doctor Quality Gate
```

Short description:

```text
Catch broken Agent Skills before they land in your repository.
```

Long description:

```text
Skill Doctor is a CI quality gate for Agent Skills. It checks publishing quality and compares pull requests against their base commit to explain changes to triggers, tool restrictions, instructions, scripts, references, and assets. Reports include deterministic risk evidence, before/after scores, workflow annotations, Markdown summaries, and JSON. Static scans also support SARIF. No scanned scripts are executed, no API key is needed, and no write permissions or PR comments are required. Risk levels are review heuristics, not security verdicts.
```

Primary workflow snippet:

```yaml
- uses: San-Z1/skill-doctor@v1
  with:
    path: skills
    fail-on: warning
    fail-on-risk: high
```

## Release Steps

1. Run `./scripts/verify-release.ps1`.
2. Publish an immutable `v1.1.0` tag and release with the wheel and standalone Skill ZIP.
3. Confirm remote CI passes on the release commit, then move `v1` to that same commit with a tag lease.
4. Update the Marketplace release from the GitHub release page if required.
5. Keep the existing Marketplace link in README; do not create a second listing.

## Launch Positioning

- Lead with the outcome: "stop broken skills from landing in pull requests."
- Show the 60-second workflow snippet before deeper documentation.
- Use the quality score screenshot or terminal recording as the visual.
- Ask for feedback from maintainers of Agent Skill repositories, not generic stars.
