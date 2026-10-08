# Launch Post Draft

Use this as the first public announcement. Keep the post focused on the problem and ask for feedback from maintainers.

## Short Version

```text
I built Skill Doctor: a CI quality gate for Agent Skills.

New in v1.1: it explains what a Skill PR changes: triggers, tool permissions, instructions, scripts, and resources. A Skill can keep a 100/100 quality score while expanding access from Read to Read plus Write; the change review flags that separately.

Try it locally: skill-doctor diff skills --base-ref main --fail-on-risk high

Use it in 60 seconds:

- uses: San-Z1/skill-doctor@v1
  with:
    path: skills
    fail-on: warning
    fail-on-risk: high

Repo: https://github.com/San-Z1/skill-doctor

I am looking for feedback from people maintaining Agent Skill repositories.
```

## Longer Version

```text
Agent Skills are easy to write, but surprisingly easy to break.

The problems are usually small:

- a resource file is mentioned but does not exist
- a helper file exists but is never referenced
- the trigger description is too vague
- two sibling skills compete for the same task
- a skill asks for broader tool access than it needs

I built Skill Doctor to catch those issues before they land in a repository.

It runs locally or in CI and gives each static scan a quality score and grade. Version 1.1 adds Git-based change review, explainable risk evidence, tool/trigger deltas, resource hashes, and before/after findings. On pull requests the Action uses the base commit automatically and writes a job summary without a write token. No API keys or model calls; scanned scripts are never executed. Risk heuristics are not a security verdict.

Quick setup:

- uses: San-Z1/skill-doctor@v1
  with:
    path: skills
    fail-on: warning
    fail-on-risk: high

Repo: https://github.com/San-Z1/skill-doctor

If you maintain an Agent Skill repo, I would love feedback on which checks should be stricter, which ones should be optional, and what would make the report more useful in pull requests.
```

## Where To Share

- GitHub Discussions in communities that talk about Agent Skills.
- Developer communities focused on AI agents and automation.
- Social posts with a short terminal GIF.
- Pull requests that fix real skill quality issues and mention the tool only as context.

## Follow-Up Post Ideas

- "I scanned public Agent Skills and these quality issues kept appearing."
- "How to add a quality gate to an Agent Skill repository in one minute."
- "What makes a SKILL.md file easy for agents to use?"
