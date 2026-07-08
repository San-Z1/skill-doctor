# GitHub Actions Marketplace Launch Checklist

Use this checklist when publishing Skill Doctor as a GitHub Action and preparing the repository for discovery.

## Repository Setup

- Keep `action.yml` in the repository root.
- Keep the `v1` tag updated to the latest stable action commit.
- Use a short About description:

```text
CI quality gate for Agent Skills.
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

Short description:

```text
Catch broken Agent Skills before they land in your repository.
```

Long description:

```text
Skill Doctor is a CI quality gate for Agent Skills. It scans SKILL.md files and bundled resources for vague triggers, broken resource links, oversized instructions, competing skill descriptions, and broad tool hints. Reports are available as workflow annotations, Markdown summaries, JSON, and SARIF, with a quality score and grade for quick review.
```

Primary workflow snippet:

```yaml
- uses: San-Z1/skill-doctor@v1
  with:
    path: skills
    fail-on: warning
```

## Release Steps

1. Run `./scripts/verify-release.ps1`.
2. Confirm the `v1` tag points at the release commit.
3. Draft a GitHub release from the `v1` tag.
4. Publish the action from the GitHub release page.
5. Add the Marketplace link to `README.md` after the listing is live.

## Launch Positioning

- Lead with the outcome: "stop broken skills from landing in pull requests."
- Show the 60-second workflow snippet before deeper documentation.
- Use the quality score screenshot or terminal recording as the visual.
- Ask for feedback from maintainers of Agent Skill repositories, not generic stars.
