param(
    [string]$OutputPath = "..\skill-doctor-release.zip"
)

$ErrorActionPreference = "Stop"

$root = (Get-Location).Path.TrimEnd('\', '/')
$rootPrefix = $root + [System.IO.Path]::DirectorySeparatorChar
$resolvedOutput = [System.IO.Path]::GetFullPath((Join-Path $root $OutputPath))
$excludeDirectories = @(".git", ".pytest_cache", "dist", "build", "__pycache__")
$excludeSuffixes = @(".egg-info")

if (Test-Path -LiteralPath $resolvedOutput) {
    Remove-Item -LiteralPath $resolvedOutput -Force
}

$items = Get-ChildItem -Force -Recurse | Where-Object {
    $fullName = $_.FullName
    if ($fullName.StartsWith($rootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        $relative = $fullName.Substring($rootPrefix.Length)
    } else {
        $relative = $_.Name
    }
    $parts = $relative -split '[\\/]'
    foreach ($part in $parts) {
        if ($excludeDirectories -contains $part) {
            return $false
        }
        foreach ($suffix in $excludeSuffixes) {
            if ($part.EndsWith($suffix, [System.StringComparison]::OrdinalIgnoreCase)) {
                return $false
            }
        }
    }
    return -not $_.PSIsContainer
}

Compress-Archive -Path $items.FullName -DestinationPath $resolvedOutput -Force
Get-Item -LiteralPath $resolvedOutput | Select-Object FullName, Length
