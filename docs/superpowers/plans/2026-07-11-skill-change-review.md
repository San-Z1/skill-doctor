# Skill Change Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic Git-based Agent Skill change review to the existing CLI and Marketplace Action without breaking current static scan commands.

**Architecture:** Build immutable snapshots from the existing discovery and analysis pipeline, compare baseline and current snapshots in a pure change engine, then classify and render structured changes. A separate Git loader materializes a baseline target in a temporary directory without touching the working tree; the CLI and Action only orchestrate these focused modules.

**Tech Stack:** Python 3.10+, standard library (`argparse`, `dataclasses`, `hashlib`, `subprocess`, `tarfile`, `tempfile`), pytest, PowerShell release scripts, GitHub composite Actions.

---

## File Map

- Create `src/skill_doctor/change_models.py`: immutable snapshot, change, and report records plus risk ordering.
- Create `src/skill_doctor/snapshot.py`: normalize descriptions/tools, hash resources, and build snapshot sets using the existing analyzer.
- Create `src/skill_doctor/change_engine.py`: pair skills, calculate deltas, and assign deterministic risks.
- Create `src/skill_doctor/git_baseline.py`: safely read a target tree from a Git ref into a temporary directory.
- Create `src/skill_doctor/change_reporting.py`: Markdown, JSON, and workflow annotation renderers for change reports.
- Modify `src/skill_doctor/cli.py`: dispatch the new `diff` command while preserving legacy scan syntax.
- Create focused tests in `tests/test_snapshot.py`, `tests/test_change_engine.py`, `tests/test_git_baseline.py`, `tests/test_change_reporting.py`, and `tests/test_diff_cli.py`.
- Modify `action.yml` and `tests/test_release_assets.py`: expose automatic pull-request comparison and risk gating.
- Modify `skills/skill-doctor/SKILL.md` and `skills/skill-doctor/references/finding-codes.md`: teach the packaged Skill to run and explain change review.
- Modify `README.md`, `CHANGELOG.md`, `pyproject.toml`, `docs/distribution/marketplace.md`, `docs/release-checklist.md`, and `scripts/record-demo.ps1`; create `docs/releases/v1.1.0.md`.

### Task 1: Define Snapshot And Change Records

**Files:**
- Create: `src/skill_doctor/change_models.py`
- Test: `tests/test_snapshot.py`

- [ ] **Step 1: Write the failing model and snapshot-shape test**

```python
from pathlib import Path

from skill_doctor.change_models import ResourceSnapshot, risk_at_least
from skill_doctor.snapshot import snapshot_target


def write_skill(root: Path) -> None:
    skill = root / "review-api"
    (skill / "scripts").mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        "---\n"
        "name: review-api\n"
        "description: Use when reviewing API changes for compatibility risks.\n"
        "allowed-tools: Read, Grep\n"
        "---\n\n"
        "# Review API\n\nRun scripts/check.py after reading the change.\n",
        encoding="utf-8",
    )
    (skill / "scripts" / "check.py").write_text("print('check')\n", encoding="utf-8")


def test_snapshot_target_normalizes_skill_state(tmp_path: Path) -> None:
    write_skill(tmp_path)

    result = snapshot_target(tmp_path)

    assert result.score == 100
    assert len(result.skills) == 1
    skill = result.skills[0]
    assert skill.name == "review-api"
    assert skill.relative_path == "review-api"
    assert skill.trigger_terms == ("api", "changes", "compatibility", "reviewing", "risks")
    assert skill.allowed_tools == ("Grep", "Read")
    assert skill.resources == (
        ResourceSnapshot(
            path="scripts/check.py",
            kind="scripts",
            sha256=skill.resources[0].sha256,
        ),
    )
    assert len(skill.resources[0].sha256) == 64


def test_risk_at_least_treats_none_as_disabled() -> None:
    assert risk_at_least("high", "high") is True
    assert risk_at_least("medium", "high") is False
    assert risk_at_least("high", "none") is False
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `python -m pytest tests/test_snapshot.py -q`

Expected: FAIL during collection because `skill_doctor.change_models` and `skill_doctor.snapshot` do not exist.

- [ ] **Step 3: Add immutable records and risk comparison**

Create `src/skill_doctor/change_models.py` with these public records and exact field names:

```python
from __future__ import annotations

from dataclasses import dataclass

from .models import Finding


RISK_RANK = {"none": 0, "low": 1, "medium": 2, "high": 3}
RISKS = frozenset(RISK_RANK)


@dataclass(frozen=True)
class ResourceSnapshot:
    path: str
    kind: str
    sha256: str


@dataclass(frozen=True)
class SkillSnapshot:
    name: str
    relative_path: str
    description: str
    trigger_terms: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    body_nonempty_lines: int
    body_word_count: int
    resources: tuple[ResourceSnapshot, ...]
    findings: tuple[Finding, ...]
    score: int
    grade: str


@dataclass(frozen=True)
class SnapshotSet:
    skills: tuple[SkillSnapshot, ...]
    score: int
    grade: str


@dataclass(frozen=True)
class SkillChange:
    name: str
    kind: str
    old_path: str | None
    new_path: str | None
    risk: str
    reasons: tuple[str, ...]
    trigger_terms_added: tuple[str, ...] = ()
    trigger_terms_removed: tuple[str, ...] = ()
    tools_added: tuple[str, ...] = ()
    tools_removed: tuple[str, ...] = ()
    resources_added: tuple[str, ...] = ()
    resources_removed: tuple[str, ...] = ()
    resources_modified: tuple[str, ...] = ()
    findings_introduced: tuple[str, ...] = ()
    findings_resolved: tuple[str, ...] = ()
    score_before: int | None = None
    score_after: int | None = None


@dataclass(frozen=True)
class ChangeSummary:
    skills_added: int
    skills_removed: int
    skills_modified: int
    skills_moved: int


@dataclass(frozen=True)
class ChangeReport:
    schema_version: int
    base_ref: str
    target: str
    overall_risk: str
    baseline_score: int
    current_score: int
    summary: ChangeSummary
    changes: tuple[SkillChange, ...]


def risk_at_least(actual: str, threshold: str) -> bool:
    if threshold == "none":
        return False
    return RISK_RANK[actual] >= RISK_RANK[threshold]
```

- [ ] **Step 4: Add snapshot construction**

Create `src/skill_doctor/snapshot.py`. Use `discover_skills(target)` and `analyze_skills(skills, root=target)` once per target. Normalize `allowed-tools` with `re.split(r"[,\\s]+", value)`, normalize trigger terms with lowercase alphanumeric tokens minus the analyzer stopwords, and hash every regular file under `scripts`, `references`, and `assets` with SHA-256.

The module must expose:

```python
def snapshot_target(target: Path, *, body_line_limit: int = 180) -> SnapshotSet:
    ...
```

Assign findings to a skill when the finding path equals its relative path, starts with `<relative_path>/`, or the target itself is one skill. Calculate per-skill score with `calculate_quality_score` and `grade_for_score`; use the full analyzer report for the `SnapshotSet` score and grade.

- [ ] **Step 5: Run snapshot tests and the existing analyzer tests**

Run: `python -m pytest tests/test_snapshot.py tests/test_analyzer.py -q`

Expected: PASS.

- [ ] **Step 6: Commit the snapshot foundation**

```bash
git add src/skill_doctor/change_models.py src/skill_doctor/snapshot.py tests/test_snapshot.py
git commit -m "feat: snapshot agent skill state"
```

### Task 2: Implement Deterministic Change And Risk Analysis

**Files:**
- Create: `src/skill_doctor/change_engine.py`
- Test: `tests/test_change_engine.py`

- [ ] **Step 1: Write failing tests for all risk classes**

Use a `make_skill()` helper that returns `SkillSnapshot` with defaults and overrides. Add tests with these exact expectations:

```python
def test_tool_expansion_is_high_risk() -> None:
    report = compare_snapshot_sets(
        make_set(make_skill(allowed_tools=("Read",))),
        make_set(make_skill(allowed_tools=("Grep", "Read"))),
        base_ref="main",
        target="skills",
    )
    assert report.overall_risk == "high"
    assert report.changes[0].tools_added == ("Grep",)
    assert "tool permissions expanded" in report.changes[0].reasons


def test_script_change_is_medium_risk() -> None:
    old = make_skill(resources=(resource("scripts/check.py", "old"),))
    new = make_skill(resources=(resource("scripts/check.py", "new"),))
    change = compare(old, new)
    assert change.risk == "medium"
    assert change.resources_modified == ("scripts/check.py",)


def test_small_instruction_change_is_low_risk() -> None:
    change = compare(
        make_skill(body_nonempty_lines=20, body_word_count=100),
        make_skill(body_nonempty_lines=22, body_word_count=108),
    )
    assert change.risk == "low"


def test_removed_skill_is_high_risk() -> None:
    report = compare_snapshot_sets(
        make_set(make_skill()),
        make_set(),
        base_ref="main",
        target="skills",
    )
    assert report.changes[0].kind == "removed"
    assert report.changes[0].risk == "high"


def test_trigger_threshold_requires_material_change() -> None:
    small = compare(
        make_skill(trigger_terms=("api", "review", "schema", "compatibility")),
        make_skill(trigger_terms=("api", "review", "schema", "migration")),
    )
    material = compare(
        make_skill(trigger_terms=("api", "review", "schema", "compatibility")),
        make_skill(trigger_terms=("database", "migration", "rollback", "safety")),
    )
    assert small.risk == "low"
    assert material.risk == "medium"


def test_score_drop_boundary_is_medium_risk() -> None:
    assert compare(make_skill(score=100), make_skill(score=90)).risk == "medium"
    assert compare(make_skill(score=100), make_skill(score=91)).risk == "low"


def test_instruction_growth_requires_percent_and_absolute_thresholds() -> None:
    assert compare(
        make_skill(body_nonempty_lines=20, body_word_count=100),
        make_skill(body_nonempty_lines=30, body_word_count=126),
    ).risk == "medium"
    assert compare(
        make_skill(body_nonempty_lines=4, body_word_count=10),
        make_skill(body_nonempty_lines=6, body_word_count=15),
    ).risk == "low"
```

Also test wildcard addition, a newly introduced error finding, a newly broad description finding, a resource deletion, a new skill with and without a script, folder moves, finding resolution, unchanged snapshots, and highest-risk aggregation.

- [ ] **Step 2: Run the engine tests and verify RED**

Run: `python -m pytest tests/test_change_engine.py -q`

Expected: FAIL because `skill_doctor.change_engine` does not exist.

- [ ] **Step 3: Implement comparison helpers and risk accumulation**

Create `src/skill_doctor/change_engine.py` with public entry point:

```python
def compare_snapshot_sets(
    baseline: SnapshotSet,
    current: SnapshotSet,
    *,
    base_ref: str,
    target: str,
) -> ChangeReport:
    ...
```

Use dictionaries keyed by `SkillSnapshot.name`. Added and removed names become changes directly; shared names call `_compare_skill(old, new)`. Do not emit a `SkillChange` for identical snapshots. Sort changes by name for deterministic output. Populate `ChangeSummary` by counting added, removed, modified, and moved records; a shared name with only a relative-path change is `moved`, while a shared name with path and content changes is `modified` and increments `skills_moved` as well.

Use a local `_RiskCollector` that stores `(risk, reason)` pairs and returns the highest rank. Implement material trigger change as at least two added/removed terms or a symmetric-difference ratio of at least `0.30` against the smaller non-empty term set. Implement instruction growth when either line or word count grows by more than `25%` and by at least `10` absolute units.

Compare findings by `(severity, code, message)` and expose introduced/resolved values as sorted strings formatted `<severity>:<code>`.

- [ ] **Step 4: Run the focused tests and refactor only after GREEN**

Run: `python -m pytest tests/test_change_engine.py tests/test_snapshot.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the change engine**

```bash
git add src/skill_doctor/change_engine.py tests/test_change_engine.py
git commit -m "feat: classify agent skill changes"
```

### Task 3: Load Git Baselines Without Touching The Worktree

**Files:**
- Create: `src/skill_doctor/git_baseline.py`
- Test: `tests/test_git_baseline.py`

- [ ] **Step 1: Write failing Git integration tests**

Create a temporary repository with `git init`, local test identity, one committed `skills/demo/SKILL.md`, and an uncommitted current edit. Test this contract:

```python
def test_baseline_target_reads_committed_tree_without_touching_worktree(tmp_path: Path) -> None:
    repo = make_repo(tmp_path)
    current = repo / "skills" / "demo" / "SKILL.md"
    current.write_text(current.read_text(encoding="utf-8") + "\nCurrent change.\n", encoding="utf-8")
    before_status = git(repo, "status", "--porcelain")

    with baseline_target(repo, "HEAD", repo / "skills") as baseline:
        baseline_text = (baseline / "demo" / "SKILL.md").read_text(encoding="utf-8")
        assert "Current change." not in baseline_text

    assert git(repo, "status", "--porcelain") == before_status
```

Add tests asserting `BaselineError` for a non-Git directory, unknown ref, a target outside the repository, a target absent from the baseline, and archived links. Verify the temporary directory no longer exists after the context manager exits.

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_git_baseline.py -q`

Expected: FAIL because `skill_doctor.git_baseline` does not exist.

- [ ] **Step 3: Implement safe archive extraction**

Create:

```python
class BaselineError(ValueError):
    pass


@contextmanager
def baseline_target(repo: Path, base_ref: str, target: Path) -> Iterator[Path]:
    ...
```

Resolve the repository root using `git -C <repo> rev-parse --show-toplevel`, ensure the target resolves under that root, and verify `<base_ref>^{commit}`. Read bytes with `git archive --format=tar <base_ref> -- <relative-target>`.

Open the archive from `io.BytesIO`. Reject symbolic links, hard links, devices, and any member whose resolved destination leaves the temporary root. Extract regular files manually with `shutil.copyfileobj`; create directories explicitly. Yield the extracted target path and rely on `TemporaryDirectory` for cleanup.

Map all subprocess failures to concise `BaselineError` messages that include the ref or target but not a Python traceback.

- [ ] **Step 4: Run Git loader and discovery tests**

Run: `python -m pytest tests/test_git_baseline.py tests/test_discovery.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the Git loader**

```bash
git add src/skill_doctor/git_baseline.py tests/test_git_baseline.py
git commit -m "feat: load skill baselines from git"
```

### Task 4: Render Stable Change Reports

**Files:**
- Create: `src/skill_doctor/change_reporting.py`
- Test: `tests/test_change_reporting.py`

- [ ] **Step 1: Write failing rendering contract tests**

Build one `ChangeReport` containing a medium-risk modified skill and assert:

```python
def test_markdown_report_explains_risk_evidence() -> None:
    output = render_change_markdown(sample_report())
    assert output.startswith("# Skill Doctor Change Review")
    assert "Overall risk: **MEDIUM**" in output
    assert "Quality score: 100 -> 90 (-10)" in output
    assert "tool permissions expanded" in output


def test_json_report_has_versioned_schema() -> None:
    parsed = json.loads(render_change_json(sample_report()))
    assert parsed["schema_version"] == 1
    assert parsed["base_ref"] == "main"
    assert parsed["target"] == "skills"
    assert parsed["overall_risk"] == "medium"
    assert parsed["summary"]["skills_modified"] == 1
    assert isinstance(parsed["changes"], list)


def test_github_report_only_annotates_medium_and_high() -> None:
    output = render_change_github(report_with_low_medium_high_changes())
    assert "::notice title=skill-change-review::" in output
    assert "::warning file=medium-skill" in output
    assert "::error file=high-skill" in output
    assert "file=low-skill" not in output


def test_no_change_markdown_is_not_empty() -> None:
    assert "No behavior or quality changes detected." in render_change_markdown(empty_report())
```

- [ ] **Step 2: Run the tests and verify RED**

Run: `python -m pytest tests/test_change_reporting.py -q`

Expected: FAIL because `skill_doctor.change_reporting` does not exist.

- [ ] **Step 3: Implement deterministic renderers**

Expose:

```python
def render_change_markdown(report: ChangeReport) -> str: ...
def render_change_json(report: ChangeReport) -> str: ...
def render_change_github(report: ChangeReport) -> str: ...
```

Use `dataclasses.asdict` for JSON with `indent=2` and `sort_keys=True`. Markdown must include base ref, target, changed-skill count, overall risk, score delta, and one section per skill with reasons and non-empty delta lists. Reuse the annotation escaping behavior from `reporting.py` by moving the two private escape helpers to public-neutral names in a small shared section or duplicating the four-line escaping logic; do not change existing output.

Map high risk to `error`, medium to `warning`, low to no file annotation, plus one final `notice` summary.

- [ ] **Step 4: Run old and new reporting tests**

Run: `python -m pytest tests/test_change_reporting.py tests/test_reporting.py -q`

Expected: PASS with unchanged static report snapshots.

- [ ] **Step 5: Commit report rendering**

```bash
git add src/skill_doctor/change_reporting.py tests/test_change_reporting.py
git commit -m "feat: render skill change reviews"
```

### Task 5: Add The Backward-Compatible Diff CLI

**Files:**
- Modify: `src/skill_doctor/cli.py`
- Create: `tests/test_diff_cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing end-to-end CLI tests**

Create a temporary Git repository with a committed baseline skill, modify its description and tools, then invoke the package exactly as users will:

```python
result = run_cli(repo, "diff", "--base-ref", "HEAD", "skills", "--format", "json")
assert result.returncode == 0
report = json.loads(result.stdout)
assert report["schema_version"] == 1
assert report["overall_risk"] == "high"

gated = run_cli(
    repo,
    "diff",
    "--base-ref",
    "HEAD",
    "skills",
    "--format",
    "markdown",
    "--fail-on-risk",
    "high",
)
assert gated.returncode == 1
```

Add tests for `--fail-on-risk none`, unknown refs returning `2` on stderr, unsupported `sarif` producing argparse exit `2`, and no changes returning `0`. Keep the existing `test_module_command_runs_from_repo_without_install` unchanged as the legacy compatibility proof.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python -m pytest tests/test_diff_cli.py tests/test_cli.py -q`

Expected: new diff tests FAIL because the existing parser treats `diff` as a target path; all legacy CLI tests still PASS.

- [ ] **Step 3: Split scan and diff orchestration without changing scan behavior**

Refactor `main()` into this dispatch shape:

```python
def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "diff":
        return _main_diff(args[1:])
    return _main_scan(args)
```

Move the existing parser body unchanged into `_main_scan`. Add `_main_diff` with positional `target`, required `--base-ref`, formats `markdown/json/github`, `--fail-on-risk` choices from `RISKS`, and optional `--body-line-limit` default `180`.

Resolve the Git root from `Path.cwd()`, open `baseline_target`, snapshot both targets, call `compare_snapshot_sets`, render, and return `1` only when `risk_at_least(report.overall_risk, args.fail_on_risk)` is true. Catch `BaselineError`, `FrontmatterError`, `FileNotFoundError`, and `OSError` and return `2` after printing one stderr line.

- [ ] **Step 4: Verify all CLI and core tests**

Run: `python -m pytest tests/test_diff_cli.py tests/test_cli.py tests/test_change_engine.py tests/test_git_baseline.py -q`

Expected: PASS.

- [ ] **Step 5: Commit the CLI workflow**

```bash
git add src/skill_doctor/cli.py tests/test_cli.py tests/test_diff_cli.py
git commit -m "feat: compare skill changes from git"
```

### Task 6: Integrate Pull-Request Review Into The Marketplace Action

**Files:**
- Modify: `action.yml`
- Modify: `tests/test_release_assets.py`

- [ ] **Step 1: Add failing Action contract tests**

Extend `test_repository_exposes_github_action_entrypoint` with:

```python
assert "compare-ref:" in text
assert "fail-on-risk:" in text
assert "GITHUB_BASE_REF" in text
assert 'skill-doctor diff' in text
assert '--fail-on-risk' in text
assert 'git fetch --no-tags --depth=1' in text
```

Add an assertion that the existing static `skill-doctor "${args[@]}"` invocation and summary remain present.

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_release_assets.py::test_repository_exposes_github_action_entrypoint -q`

Expected: FAIL on the missing `compare-ref` assertion.

- [ ] **Step 3: Add optional comparison inputs and one review step**

Add inputs:

```yaml
  compare-ref:
    description: Git ref to compare with the current workspace. Pull requests use the base branch when empty.
    required: false
    default: ""
  fail-on-risk:
    description: Lowest change risk that should fail the workflow.
    required: false
    default: none
```

Add a step enabled by `${{ github.event_name == 'pull_request' || inputs.compare-ref != '' }}`. Resolve an empty input from `GITHUB_BASE_REF`; verify the ref locally and fetch only the requested branch when necessary. Run GitHub output with the configured threshold, preserve its exit code, then append Markdown output to `$GITHUB_STEP_SUMMARY` and exit with the preserved status.

Do not request repository write permissions and do not add comment-writing code.

- [ ] **Step 4: Run Action contract and complete tests**

Run: `python -m pytest tests/test_release_assets.py -q`

Expected: PASS.

- [ ] **Step 5: Commit Action integration**

```bash
git add action.yml tests/test_release_assets.py
git commit -m "feat: review skill changes in pull requests"
```

### Task 7: Update And Test The Packaged Agent Skill

**Files:**
- Modify: `skills/skill-doctor/SKILL.md`
- Modify: `skills/skill-doctor/references/finding-codes.md`
- Modify: `tests/test_release_assets.py`

- [ ] **Step 1: Add the failing packaged-Skill behavior test before editing it**

```python
def test_packaged_skill_teaches_git_change_review() -> None:
    skill = (ROOT / "skills" / "skill-doctor" / "SKILL.md").read_text(encoding="utf-8")
    reference = (
        ROOT / "skills" / "skill-doctor" / "references" / "finding-codes.md"
    ).read_text(encoding="utf-8")

    assert "diff --base-ref" in skill
    assert "low / medium / high" in skill
    assert "Do not execute scripts" in skill
    assert "Risk levels" in reference
    assert "tool permissions expanded" in reference
```

- [ ] **Step 2: Run the test and verify RED**

Run: `python -m pytest tests/test_release_assets.py::test_packaged_skill_teaches_git_change_review -q`

Expected: FAIL because the packaged Skill only explains static scanning.

- [ ] **Step 3: Teach the smallest complete change-review workflow**

Update the frontmatter description to include reviewing Skill pull requests and Git changes while retaining the current static-review triggers. Add a workflow branch:

```bash
python skills/skill-doctor/scripts/run_skill_doctor.py diff --base-ref <ref> <target> --format markdown
```

Tell the agent to use JSON for automation, explain `low / medium / high`, surface exact risk reasons, and never execute scripts found in either snapshot. Add a concise Risk Levels section to the reference file with the classifier rules from the approved design.

- [ ] **Step 4: Run the packaged Skill test and self-scan**

Run: `python -m pytest tests/test_release_assets.py -q`

Run: `python -m skill_doctor skills --fail-on warning`

Expected: both commands PASS and the self-scan reports no findings.

- [ ] **Step 5: Commit the Skill update**

```bash
git add skills/skill-doctor/SKILL.md skills/skill-doctor/references/finding-codes.md tests/test_release_assets.py
git commit -m "feat: teach skill change review"
```

### Task 8: Document, Demo, And Version The Release

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `pyproject.toml`
- Modify: `docs/distribution/marketplace.md`
- Modify: `docs/release-checklist.md`
- Modify: `scripts/record-demo.ps1`
- Create: `docs/releases/v1.1.0.md`
- Modify: `tests/test_release_assets.py`

- [ ] **Step 1: Add failing documentation and version assertions**

```python
def test_readme_promotes_pull_request_change_review() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "skill-doctor diff --base-ref main skills" in readme
    assert "Behavior change" in readme
    assert "fail-on-risk: high" in readme


def test_v1_1_release_assets_are_consistent() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    release = (ROOT / "docs" / "releases" / "v1.1.0.md").read_text(encoding="utf-8")
    marketplace = (ROOT / "docs" / "distribution" / "marketplace.md").read_text(encoding="utf-8")
    assert 'version = "1.1.0"' in project
    assert "## 1.1.0 - 2026-07-11" in changelog
    assert "Skill change review" in release
    assert "fail-on-risk" in marketplace
```

- [ ] **Step 2: Run the assertions and verify RED**

Run: `python -m pytest tests/test_release_assets.py -q`

Expected: FAIL on the new README and release assertions.

- [ ] **Step 3: Update README first-screen positioning and examples**

Keep the current 60-second scan setup. Add a compact pull-request change review section immediately after it with:

```bash
skill-doctor diff --base-ref main skills
```

Show a short Markdown result containing overall risk, score delta, one changed Skill, and evidence. Extend the Action snippet with `fail-on-risk: high`; explain that pull requests automatically compare the base branch and require no write permission.

- [ ] **Step 4: Update release and Marketplace material**

Set `pyproject.toml` version to `1.1.0`. Add a dated changelog section listing Git snapshots, deterministic risk levels, three change-report formats, Action integration, and compatibility. Create `docs/releases/v1.1.0.md` with installation, local command, Action snippet, highlights, compatibility, and static-safety statement.

Update Marketplace copy to lead with “understand how a pull request changes Agent behavior,” document `compare-ref` and `fail-on-risk`, and retain static quality-gate language.

Add diff checks to the release checklist. Update `scripts/record-demo.ps1` to run `skill-doctor diff --base-ref HEAD~1 skills --format markdown` when `HEAD~1` exists, otherwise print a clear skip message while retaining existing demo scans.

- [ ] **Step 5: Run documentation tests and inspect demo output**

Run: `python -m pytest tests/test_release_assets.py -q`

Run: `./scripts/record-demo.ps1`

Expected: tests PASS; demo prints static reports plus a change-review report or the documented no-history skip.

- [ ] **Step 6: Commit release documentation**

```bash
git add README.md CHANGELOG.md pyproject.toml docs/distribution/marketplace.md docs/release-checklist.md docs/releases/v1.1.0.md scripts/record-demo.ps1 tests/test_release_assets.py
git commit -m "docs: prepare skill doctor v1.1.0"
```

### Task 9: Complete Verification And Publish

**Files:**
- Verify all changed files
- Regenerate: `../skill-doctor-release.zip`

- [ ] **Step 1: Run the complete test suite**

Run: `python -m pytest -q`

Expected: all tests PASS with no warnings or errors.

- [ ] **Step 2: Run focused behavior demos**

Run: `python -m skill_doctor examples/good-skills --format json`

Expected: exit `0`, score `100`, no findings.

Run: `python -m skill_doctor examples/problematic-skills --format markdown`

Expected: exit `1` due to existing error findings.

Run: `python -m skill_doctor diff --base-ref a5293e6 skills --format markdown --fail-on-risk none`

Expected: exit `0`, at least one modified Skill, and an explained overall risk.

- [ ] **Step 3: Run the full release verifier**

Run: `./scripts/verify-release.ps1`

Expected: tests PASS, wheel builds, all demos and invariant scans pass, the release zip is regenerated, and output ends with `Skill Doctor release verification passed.`

- [ ] **Step 4: Audit scope and public history before publishing**

Run: `git status --short`

Expected: no tracked or untracked changes except generated ignored build artifacts.

Run: `git diff a5293e6..HEAD --stat`

Expected: only approved design, implementation, tests, Action, packaged Skill, and release documentation files.

Run the existing public marker scan from `scripts/verify-release.ps1` against files and reachable commit messages.

Expected: no matches.

- [ ] **Step 5: Push the verified release commit**

```bash
git push origin main
git tag -a v1.1.0 -m "Skill Doctor v1.1.0"
git push origin v1.1.0
git tag -f v1
git push origin v1 --force
```

Expected: `main`, immutable `v1.1.0`, and floating `v1` all point to the intended verified history (`v1` and `v1.1.0` resolve to the same commit).

- [ ] **Step 6: Verify remote release state before claiming completion**

Run:

```bash
git ls-remote origin refs/heads/main refs/tags/v1 refs/tags/v1^{} refs/tags/v1.1.0 refs/tags/v1.1.0^{}
```

Expected: remote `main`, peeled `v1`, and peeled `v1.1.0` resolve to the release commit. Then create or verify the GitHub `v1.1.0` release using `docs/releases/v1.1.0.md`, and confirm the Marketplace listing still resolves through `San-Z1/skill-doctor@v1`.
