param(
    [Parameter(Mandatory = $true)]
    [string]$RemoteUrl,

    [string]$CommitMessage = "Initial Skill Doctor project"
)

$ErrorActionPreference = "Stop"

function Invoke-Step {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Label,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Command
    )

    Write-Host "==> $Label"
    & $Command
}

function Assert-GitIdentity {
    $name = git config user.name
    $email = git config user.email
    if ([string]::IsNullOrWhiteSpace($name) -or [string]::IsNullOrWhiteSpace($email)) {
        throw "Git identity is not configured. Run: git config user.name `"Your Name`"; git config user.email `"you@example.com`""
    }
}

function Assert-RemoteUrl {
    if ($RemoteUrl -notmatch '^https://github\.com/[^/]+/[^/]+(\.git)?$') {
        throw "RemoteUrl must look like https://github.com/<owner>/<repo>.git"
    }
}

function Get-OriginRemote {
    $remotes = git remote
    if ($LASTEXITCODE -ne 0) {
        throw "Could not list git remotes."
    }
    if ($remotes -notcontains "origin") {
        return ""
    }
    return git remote get-url origin
}

Invoke-Step "Check git identity" { Assert-GitIdentity }
Invoke-Step "Check GitHub remote URL" { Assert-RemoteUrl }
Invoke-Step "Run tests" { python -m pytest -q }
Invoke-Step "Build wheel" { python -m pip wheel . --no-deps -w dist }
Invoke-Step "Run clean example scan" { python -m skill_doctor examples\good-skills --format json }
Invoke-Step "Run problematic example scan" {
    python -m skill_doctor examples\problematic-skills --format markdown
    if ($LASTEXITCODE -ne 1) {
        throw "Problematic example scan should exit with 1 because it contains an error finding."
    }
}
Invoke-Step "Check public brand markers" {
    $pattern = ("co" + "dex|open" + "ai|clau" + "de|anth" + "ropic")
    rg -n -i $pattern . --glob "!.git/**" --glob "!dist/**" --glob "!build/**" --glob "!.pytest_cache/**" --glob "!*.egg-info/**"
    if ($LASTEXITCODE -eq 0) {
        throw "Public brand marker scan found matches."
    }
    if ($LASTEXITCODE -ne 1) {
        throw "Public brand marker scan failed unexpectedly."
    }
}

Invoke-Step "Stage files" { git add --renormalize .; git add . }

$staged = git diff --cached --name-only
if ([string]::IsNullOrWhiteSpace($staged)) {
    Write-Host "No staged changes to commit."
} else {
    Invoke-Step "Commit staged files" { git commit -m $CommitMessage }
}

Invoke-Step "Set main branch" { git branch -M main }

$origin = Get-OriginRemote
if ([string]::IsNullOrWhiteSpace($origin)) {
    Invoke-Step "Add origin remote" { git remote add origin $RemoteUrl }
} elseif ($origin -ne $RemoteUrl) {
    Invoke-Step "Update origin remote" { git remote set-url origin $RemoteUrl }
}

Invoke-Step "Push to GitHub" { git push -u origin main }

Write-Host "Published Skill Doctor to $RemoteUrl"
