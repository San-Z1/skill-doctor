# Finding Codes

## error

- `missing-name`: `SKILL.md` has no `name` field.
- `invalid-skill-name`: the skill name is not lowercase kebab-case.
- `missing-description`: `SKILL.md` has no `description` field.

## warning

- `folder-name-mismatch`: the folder name and skill name differ.
- `missing-trigger-context`: the description does not clearly say when the skill should be used.
- `description-too-broad`: the description is likely to trigger for unrelated tasks.
- `body-too-large`: `SKILL.md` is large enough that progressive disclosure would help.
- `allowed-tools-too-broad`: `allowed-tools` uses a wildcard.
- `overlapping-description`: sibling skills have similar trigger descriptions.
- `missing-resource`: `SKILL.md` references a missing file under `scripts/`, `references/`, or `assets/`.

## info

- `orphan-resource`: a file under `scripts/`, `references/`, or `assets/` is not mentioned from `SKILL.md`.
