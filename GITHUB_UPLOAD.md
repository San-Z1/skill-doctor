# Uploading Skill Doctor to GitHub

The project is ready at `E:\Skill\skill-doctor`.

If you want to upload through the GitHub website, use:

```text
E:\Skill\skill-doctor-release.zip
```

Create an empty public repository named `skill-doctor`, upload the extracted contents, and enable GitHub Actions.

For the first GitHub release, use `docs/releases/v0.1.0.md` as the release notes.

If you want to push with git, first create an empty GitHub repository, then run:

```powershell
cd E:\Skill\skill-doctor
git config user.name "Your Name"
git config user.email "you@example.com"
./scripts/publish-github.ps1 -RemoteUrl "https://github.com/your-github-user/skill-doctor.git"
```

Before publishing, the release gate can be run locally:

```powershell
cd E:\Skill\skill-doctor
./scripts/verify-release.ps1
```

Expected result:

```text
Skill Doctor release verification passed.
```
