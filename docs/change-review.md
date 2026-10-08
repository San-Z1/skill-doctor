# Skill Change Review

## Local Review

```bash
skill-doctor diff skills --base-ref main
skill-doctor diff skills --base-ref HEAD~1 --format json
skill-doctor diff skills --base-ref main --format github --fail-on-risk high
skill-doctor diff skills/review-api/SKILL.md --base-ref main
```

Use the PR base SHA to review the whole PR. Using HEAD reviews only workspace changes after the current commit. The target must exist inside a Git repository, and the baseline must resolve locally to a commit. No checkout or index changes are performed. New collections have an empty baseline; to review a deleted Skill, compare its enclosing collection.

`--body-line-limit` is a positive integer, default 180. Diff does not use the static scan's `--config`, `--fail-on`, or SARIF format. The original `skill-doctor skills` command remains unchanged. A directory literally named `diff` can be scanned as `./diff`.

## Risk Gate

`--fail-on-risk none` is the default and does not fail on completed reviews. Choose `low`, `medium`, or `high` to fail at that level and above.

- Exit 0: comparison completed without gated risk.
- Exit 1: comparison completed and the risk threshold was reached.
- Exit 2: invalid input, unknown ref, missing target, malformed frontmatter, duplicate names, unsafe paths, or Git/filesystem failure. This is not a clean review.

The report includes added/removed/moved/modified Skills; trigger-term and tool-set changes; instruction counts; content-hashed resource changes; findings introduced/resolved; and quality scores before/after. Equal-length instruction edits are detected by hash.

See [exact classification rules](../skills/skill-doctor/references/change-risk-rules.md). The highest matching rule wins. Risk does not mean maliciousness, and low risk is not a security guarantee.

## GitHub Action

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: "3.12"
  - uses: San-Z1/skill-doctor@v1
    with:
      path: skills
      fail-on: warning
      fail-on-risk: high
```

| Input | Default | Meaning |
|---|---|---|
| `path` | `skills` | Static scan and comparison target. |
| `fail-on` | `warning` | Static finding gate. |
| `config` | empty | Static JSON config; its body line limit also applies to comparison. |
| `summary` | `true` | Append Markdown results to the job step summary. |
| `compare-ref` | PR base SHA on PR events; otherwise empty | Compare a specified commit or ref. |
| `fail-on-risk` | `none` | Change risk gate, independent of static findings. |

The Action fetches only a missing requested baseline from `origin`; failure is visible and produces exit 2. Ref-fetch input does not accept refspecs or options. A configured risk gate does not disable the static quality gate. Summaries are retained even when a gate fails. No pull-request comments or write token are required. Use ordinary `pull_request` workflows, not a privileged `pull_request_target` workflow checking out untrusted code.

## Output And Limits

JSON has `schema_version: 1` with guaranteed `base_ref`, `target`, `overall_risk`, `summary`, and `changes` keys. Additive fields are allowed; consumers should ignore unknown fields. Scores describe authoring findings, not runtime correctness.

Discovery supports one Skill or immediate Skill folders in a collection, not arbitrary recursive discovery. Frontmatter supports scalar fields, not full YAML. Trigger terms are lexical rather than semantic; resource renames are removal plus addition. A Skill name change is also removal plus addition; a folder move with the same name is paired. Diff rejects symlinks and duplicate non-empty names. The Git baseline includes only committed files, while the current side includes local edits and untracked files.

Only scripts, references, and assets are hashed. No scanned script is executed, no model is called, and no automated repair or malware/prompt-injection claim is made.
Generated Python bytecode and cache directories are excluded from resource snapshots and orphan-resource findings.

## Reproducible Demo

```bash
python scripts/demo_change_review.py
python scripts/demo_change_review.py --format json --fail-on-risk high
```

The demo creates a temporary Git repository, expands Read to Read plus Write, adds a non-executed script, and prints a real report. It cleans up without changing your repository. The second command exits 1 intentionally.
