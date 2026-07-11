# Skill Change Review Design

## Summary

Skill Doctor will expand from static validation into deterministic change review for Agent Skills. A new diff command will compare a Git baseline with the current workspace and explain how a pull request changes triggers, tool access, instructions, resources, and quality findings.

The feature will remain static: it will read skill content but never execute scripts from a scanned skill. Existing scan commands and GitHub Action inputs will remain compatible.

## Goals

- Make Agent Skill pull requests understandable without manually reading every changed file.
- Identify behavior-expanding changes before merge.
- Produce deterministic, explainable risk levels without model calls or API keys.
- Reuse the existing analyzer and report formats where practical.
- Add a distinctive pull-request workflow to the existing Marketplace Action.

## Non-Goals

The first release will not:

- modify scanned skills automatically;
- execute or sandbox scanned scripts;
- classify malware or prompt-injection threats;
- call a language model;
- post or update pull-request comments;
- replace the existing static scan.

## User Interface

### Local command

```bash
skill-doctor diff --base-ref main skills
```

Optional controls:

```bash
skill-doctor diff --base-ref main skills --format json
skill-doctor diff --base-ref main skills --format github
skill-doctor diff --base-ref main skills --fail-on-risk high
```

Supported diff output formats in the first release are `markdown`, `json`, and `github`. SARIF remains available for static scan results but is excluded from change review because behavioral changes do not map cleanly to source-code vulnerabilities.

`--fail-on-risk` accepts `none`, `low`, `medium`, or `high` and defaults to `none`. This keeps local review informative until a maintainer explicitly enables a merge gate.

### Backward compatibility

Existing commands remain valid:

```bash
skill-doctor skills --format markdown --fail-on warning
```

The implementation may internally dispatch between scan and diff modes, but it must not require existing users to add a `scan` subcommand.

### GitHub Action

The Action will add optional inputs for baseline comparison and risk gating. When comparison is enabled, it will append a change-review section to the workflow step summary and emit annotations for high- and medium-risk changes.

For pull requests, the Action will use the pull request base ref when no explicit comparison ref is supplied. If the ref is not present in the checkout, the Action may fetch that single ref before running the comparison. Static scanning will continue to work when no Git history is available.

The first release will not post pull-request comments because that requires write permissions and creates duplicate-message management concerns.

## Architecture

The feature will add four focused components.

### Baseline loader

The baseline loader verifies the Git repository and requested ref, reads the requested target tree from Git, and materializes it in a temporary directory. It must not check out files, change branches, alter the index, or modify the working tree.

Temporary files are removed after analysis. Paths extracted from Git are validated to prevent traversal outside the temporary directory.

### Snapshot builder

The snapshot builder converts each discovered skill into an immutable representation containing:

- skill name and relative directory;
- description and normalized description tokens;
- normalized `allowed-tools` values;
- non-empty line count and word count for `SKILL.md`;
- files under `scripts/`, `references/`, and `assets/` with content hashes;
- static findings, quality score, and grade.

The same builder is used for the baseline and current workspace so comparisons are symmetric.

### Change engine

The change engine pairs snapshots by skill name. It reports added, removed, and modified skills. Folder changes for the same skill name are reported as moves rather than one deletion plus one addition.

For modified skills it calculates:

- trigger terms added and removed;
- tool permissions added and removed;
- instruction line and word deltas;
- resources added, removed, or modified;
- findings introduced and resolved;
- quality score and grade changes.

The engine produces structured change records and does not contain rendering logic.

### Risk classifier and renderers

The classifier assigns a deterministic risk to each change and an overall risk equal to the highest individual risk. Renderers transform the structured report into Markdown, JSON, or GitHub annotations.

## Risk Rules

### High risk

- A wildcard tool permission is added.
- The explicit tool permission set expands.
- A new error-level static finding appears.
- A skill is removed.
- A description newly triggers `description-too-broad` or `missing-trigger-context`.

### Medium risk

- A script is added or modified.
- A resource is removed.
- Trigger terms materially change.
- The static quality score drops by at least 10 points.
- Non-empty `SKILL.md` lines or words increase by more than 25 percent, with a minimum absolute increase of 10 to avoid noise on tiny files.

Trigger terms materially change when at least two normalized non-stopword terms are added or removed, or when at least 30 percent of the smaller baseline/current trigger-token set changes. This rule makes the threshold deterministic and testable.

### Low risk

- A reference or asset is added or modified.
- Instructions change below the medium-risk size threshold.
- Static findings are resolved or quality improves.
- A new skill is added without any high- or medium-risk condition.

### No risk

- No behavior- or quality-relevant content changes.
- Only file metadata that is not part of a snapshot changes.

When several rules match, the highest risk wins. Every result lists the exact rules that caused its classification.

## Data Flow

1. Parse CLI or Action inputs.
2. Validate the working repository, target, and baseline ref.
3. Load the baseline target into a temporary directory.
4. Discover and analyze baseline and current skills using the same code paths.
5. Build immutable snapshots.
6. Pair skills and calculate structured changes.
7. Classify individual and overall risk.
8. Render the requested format.
9. Return an exit code based on `--fail-on-risk`.

## Error Handling

- Invalid arguments, a missing target, a non-Git directory, an unknown ref, Git read failures, and unparseable baseline/current skills return exit code `2` with a concise message on stderr.
- A completed comparison returns `1` only when the overall risk meets or exceeds the configured `--fail-on-risk` threshold.
- A completed comparison with no gated risk returns `0`.
- No changes produce a short successful report rather than an empty document.
- Temporary baseline data is cleaned up on success and failure.
- The Action reports baseline-fetch failures clearly and does not silently compare against an unintended ref.

## Output Contract

Markdown output starts with an overall summary containing the baseline ref, target, skills changed, overall risk, and quality score delta. It then groups changes by skill and lists evidence for every risk decision.

JSON output uses a versioned top-level schema with these keys:

```json
{
  "schema_version": 1,
  "base_ref": "main",
  "target": "skills",
  "overall_risk": "medium",
  "summary": {},
  "changes": []
}
```

The first release guarantees the presence and meaning of these top-level keys. New optional fields may be added without changing `schema_version`; removals or semantic changes require a version increase.

GitHub output emits workflow annotations for medium- and high-risk records and a compact final notice. The Action separately writes the full Markdown report to the step summary.

## Testing

Implementation will follow test-first development.

Unit tests will cover every risk rule, threshold boundary, highest-risk aggregation, skill pairing, folder moves, token normalization, and file hash comparison.

Integration tests will create temporary Git repositories and verify:

- reading a baseline commit without modifying the branch, index, or working tree;
- added, removed, moved, and modified skills;
- tool expansion, trigger changes, script changes, resource changes, score regression, and no-change cases;
- cleanup after successful and failed comparisons;
- Markdown, JSON, and GitHub output;
- `--fail-on-risk` exit behavior;
- clear errors for non-Git directories and unknown refs.

Regression tests will prove that existing scan invocations, configuration, output formats, the packaged Agent Skill, and Marketplace Action behavior remain valid. The existing public-content invariant and full release verification script remain required gates.

## Documentation And Release

- Add a first-screen README example showing a pull-request behavior summary.
- Document local diff usage and the Action comparison inputs.
- Update the packaged `skill-doctor` Skill so agents can run and interpret change reviews.
- Update finding/risk references, CHANGELOG, Marketplace copy, release checklist, and demo assets.
- Publish a compatible `v1.1.0` release after verification.
- Move the floating `v1` tag to the verified release commit so existing Marketplace users receive the compatible update.

## Acceptance Criteria

The feature is complete when:

- a user can compare a Git ref with the current skills directory using one command;
- all listed behavior changes and deterministic risk rules appear in structured output;
- risk gating produces documented exit codes;
- the GitHub Action can add a pull-request change summary without requiring write permissions;
- scanned skill scripts are never executed;
- existing scan commands remain compatible;
- the full test suite, package build, demo checks, public-content scan, and release verifier pass;
- README, packaged Skill, Marketplace guidance, changelog, and release notes describe the new workflow;
- the verified version is pushed and published as `v1.1.0`, with `v1` updated afterward.
