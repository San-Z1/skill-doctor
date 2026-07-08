$ErrorActionPreference = "Stop"

function Invoke-DemoCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$CommandText,

        [Parameter(Mandatory = $true)]
        [scriptblock]$Command,

        [int[]]$AllowedExitCodes = @(0)
    )

    Write-Host ""
    Write-Host "$ $CommandText" -ForegroundColor Cyan
    & $Command
    $exitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }
    if ($AllowedExitCodes -notcontains $exitCode) {
        throw "Command exited with ${exitCode}: $CommandText"
    }
    Start-Sleep -Milliseconds 700
}

Write-Host "Skill Doctor terminal demo" -ForegroundColor Green
Write-Host "Focus points: workflow annotations, Markdown report, and Quality score." -ForegroundColor Green
Start-Sleep -Milliseconds 900

Invoke-DemoCommand `
    -CommandText "python -m skill_doctor examples/good-skills --format markdown" `
    -Command { python -m skill_doctor examples\good-skills --format markdown }

Invoke-DemoCommand `
    -CommandText "python -m skill_doctor examples/problematic-skills --format markdown" `
    -Command { python -m skill_doctor examples\problematic-skills --format markdown } `
    -AllowedExitCodes @(1)

Invoke-DemoCommand `
    -CommandText "python -m skill_doctor examples/problematic-skills --format github" `
    -Command { python -m skill_doctor examples\problematic-skills --format github } `
    -AllowedExitCodes @(1)

Write-Host ""
Write-Host "Recording tip: run this script while recording a terminal GIF, then trim after the Quality score appears." -ForegroundColor Green
