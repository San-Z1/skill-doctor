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

Invoke-Step "Run tests" { python -m pytest -q }
Invoke-Step "Build wheel" {
    if (Test-Path dist) {
        Remove-Item -Recurse -Force dist
    }
    python -m pip wheel . --no-deps -w dist
}
Invoke-Step "Run clean example scan" {
    python -m skill_doctor examples\good-skills --format json
}
Invoke-Step "Run problematic example scan" {
    python -m skill_doctor examples\problematic-skills --format markdown
    if ($LASTEXITCODE -ne 1) {
        throw "Problematic example scan should exit with 1 because it contains an error finding."
    }
}
Invoke-Step "Run GitHub annotation example scan" {
    python -m skill_doctor examples\problematic-skills --format github
    if ($LASTEXITCODE -ne 1) {
        throw "GitHub annotation scan should exit with 1 because it contains an error finding."
    }
}
Invoke-Step "Run SARIF example scan" {
    python -c "import json, subprocess, sys; p=subprocess.run([sys.executable, '-m', 'skill_doctor', 'examples/problematic-skills', '--format', 'sarif'], text=True, capture_output=True); assert p.returncode == 1, p.returncode; data=json.loads(p.stdout); assert data['version'] == '2.1.0'; assert data['runs'][0]['results']; print('SARIF_RESULTS=%d' % len(data['runs'][0]['results']))"
}
Invoke-Step "Run config-file example scan" {
    python -m skill_doctor examples\problematic-skills --config examples\skill-doctor.config.json
    if ($LASTEXITCODE -ne 1) {
        throw "Config-file scan should exit with 1 because fail_on=warning and the example has findings."
    }
}
Invoke-Step "Self-scan packaged skill" {
    python -m skill_doctor skills --fail-on warning
}
Invoke-Step "Check unfinished markers" {
    $pattern = ("TO" + "DO|\[TO" + "DO|T" + "BD|OW" + "NER")
    rg -n $pattern .
    if ($LASTEXITCODE -eq 0) {
        throw "Unfinished marker scan found matches."
    }
    if ($LASTEXITCODE -ne 1) {
        throw "Marker scan failed unexpectedly."
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
Invoke-Step "Create clean release zip" {
    ./scripts/make-release-zip.ps1
}
Invoke-Step "Verify clean release zip" {
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $zip = [System.IO.Compression.ZipFile]::OpenRead("..\skill-doctor-release.zip")
    try {
        $matches = $zip.Entries | Where-Object { $_.FullName -match '(^|/)(\.git|\.pytest_cache|dist|build|__pycache__|.*\.egg-info)(/|$)' } | Select-Object -ExpandProperty FullName
        if ($matches) {
            throw "Release zip contains local artifacts: $($matches -join ', ')"
        }
        Write-Host "NO_LOCAL_ARTIFACTS_IN_ZIP"
        Write-Host "ENTRY_COUNT=$($zip.Entries.Count)"
    } finally {
        $zip.Dispose()
    }
}

Write-Host "Skill Doctor release verification passed."
