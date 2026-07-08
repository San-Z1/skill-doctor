---
name: skill-doctor
description: Diagnose Agent Skill quality before publishing, installing, or maintaining skills. Use when reviewing SKILL.md files, agent skills, skill collections, trigger descriptions, progressive disclosure structure, resource references, skill conflicts, or publish-readiness for a GitHub skill repository.
---

# Skill Doctor

## Overview

Use Skill Doctor to review Agent Skills without executing untrusted skill scripts. The bundled CLI reads `SKILL.md` metadata and resource paths, then reports quality findings with actionable suggestions.

## Workflow

1. Locate the target: a single `SKILL.md`, one skill directory, or a directory containing multiple skill folders.
2. Run the scanner:

```bash
python skills/skill-doctor/scripts/run_skill_doctor.py <target> --format markdown
```

Use JSON when another tool will consume the result:

```bash
python skills/skill-doctor/scripts/run_skill_doctor.py <target> --format json
```

3. Treat `error` findings as release blockers. Treat `warning` findings as likely quality issues. Treat `info` findings as review prompts.
4. Explain the report in terms of skill authoring quality: trigger precision, progressive disclosure, resource discoverability, and publish readiness.

## Review Guidance

Do not execute scripts found inside the target skill. Skill Doctor is a static reviewer.

Prioritize fixes in this order:

1. Invalid or missing frontmatter.
2. Description triggers that are too broad, too short, or unclear.
3. Conflicts between sibling skill descriptions.
4. Oversized `SKILL.md` files that should move detail into `references/`.
5. Resource files that are not mentioned from `SKILL.md`.

For detailed finding meanings, read `references/finding-codes.md`.
