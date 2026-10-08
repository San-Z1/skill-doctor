param(
    [string]$OutputPath = "..\skill-doctor-release.zip"
)

$ErrorActionPreference = "Stop"

$resolvedOutput = [System.IO.Path]::GetFullPath($OutputPath)
# The builder preserves directories and excludes .git, .pytest_cache, dist, build, and __pycache__.
python "$PSScriptRoot/build_source_archive.py" $resolvedOutput
if ($LASTEXITCODE -ne 0) {
    throw "Source archive creation failed with exit code $LASTEXITCODE."
}
Get-Item -LiteralPath $resolvedOutput | Select-Object FullName, Length
