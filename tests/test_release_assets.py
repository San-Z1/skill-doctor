from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_publish_script_has_required_safety_checks() -> None:
    script = ROOT / "scripts" / "publish-github.ps1"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "git config user.name" in text
    assert "git config user.email" in text
    assert "git remote add origin" in text
    assert "git push -u origin main" in text
    assert "pytest" in text
    assert "pip wheel" in text
    assert "Check public brand markers" in text


def test_publish_script_handles_missing_origin_remote_safely() -> None:
    script = ROOT / "scripts" / "publish-github.ps1"

    text = script.read_text(encoding="utf-8")
    assert "function Get-OriginRemote" in text
    assert "git remote get-url origin 2>$null" not in text


def test_release_zip_script_excludes_local_artifacts() -> None:
    script = ROOT / "scripts" / "make-release-zip.ps1"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert ".git" in text
    assert ".pytest_cache" in text
    assert "dist" in text
    assert "__pycache__" in text


def test_verify_release_script_runs_full_local_checklist() -> None:
    script = ROOT / "scripts" / "verify-release.ps1"

    assert script.exists()
    text = script.read_text(encoding="utf-8")
    assert "pytest" in text
    assert "pip wheel" in text
    assert "Check public brand markers" in text
    assert "make-release-zip.ps1" in text
    assert "NO_LOCAL_ARTIFACTS_IN_ZIP" in text


def test_release_checklist_mentions_publish_script() -> None:
    checklist = (ROOT / "docs" / "release-checklist.md").read_text(encoding="utf-8")

    assert "scripts/publish-github.ps1" in checklist
    assert "scripts/make-release-zip.ps1" in checklist
    assert "scripts/verify-release.ps1" in checklist


def test_repository_exposes_github_action_entrypoint() -> None:
    action = ROOT / "action.yml"

    assert action.exists()
    text = action.read_text(encoding="utf-8")
    assert "name: Skill Doctor" in text
    assert "using: composite" in text
    assert "path:" in text
    assert "fail-on:" in text
    assert 'python -m pip install "$GITHUB_ACTION_PATH"' in text
    assert "skill-doctor" in text


def test_readme_promotes_action_quick_start() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "The CI quality gate for Agent Skills" in readme
    assert "uses: San-Z1/skill-doctor@v1" in readme
    assert "gh skill install San-Z1/skill-doctor skill-doctor@v1" in readme
    assert "docs/distribution/marketplace.md" in readme
    assert "docs/distribution/launch-post.md" in readme
    assert "Quality score" in readme


def test_distribution_assets_exist_for_public_launch() -> None:
    marketplace = ROOT / "docs" / "distribution" / "marketplace.md"
    launch_post = ROOT / "docs" / "distribution" / "launch-post.md"
    demo_script = ROOT / "scripts" / "record-demo.ps1"

    assert marketplace.exists()
    assert launch_post.exists()
    assert demo_script.exists()

    marketplace_text = marketplace.read_text(encoding="utf-8")
    assert "GitHub Actions Marketplace" in marketplace_text
    assert "San-Z1/skill-doctor@v1" in marketplace_text
    assert "quality-gate" in marketplace_text

    launch_text = launch_post.read_text(encoding="utf-8")
    assert "I built Skill Doctor" in launch_text
    assert "San-Z1/skill-doctor" in launch_text
    assert "Agent Skills" in launch_text

    script_text = demo_script.read_text(encoding="utf-8")
    assert "examples/problematic-skills" in script_text
    assert "--format markdown" in script_text
    assert "Quality score" in script_text


def test_public_text_files_do_not_name_specific_agent_vendors() -> None:
    ignored_dirs = {".git", ".pytest_cache", "dist", "build", "__pycache__"}
    forbidden = ("co" + "dex", "open" + "ai", "clau" + "de", "anth" + "ropic")
    offenders: list[str] = []

    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue

        parts = path.relative_to(ROOT).parts
        if any(part in ignored_dirs or part.endswith(".egg-info") for part in parts):
            continue

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        lowered = text.lower()
        for term in forbidden:
            if term in lowered:
                offenders.append(f"{path.relative_to(ROOT).as_posix()}: {term}")

    assert not offenders, "\n".join(offenders)
