param(
    [string]$CodeqlExe = "codeql",
    [string]$Database = ".codeql/db",
    [string]$Source = ".codeql/source",
    [string]$Sarif = ".codeql/results.sarif",
    [string]$QueryPackVersion = "1.8.2",
    [string]$Suite = ""
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$CodeqlRoot = Join-Path $RepoRoot ".codeql"
$DatabasePath = Join-Path $RepoRoot $Database
$SourcePath = Join-Path $RepoRoot $Source
$SarifPath = Join-Path $RepoRoot $Sarif

function Remove-CodeqlPath {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) { return }
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $allowedRoot = (Resolve-Path -LiteralPath $CodeqlRoot).Path
    if (-not $resolved.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove path outside .codeql: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

function Invoke-Codeql {
    & $CodeqlExe @args
    if ($LASTEXITCODE -ne 0) {
        throw "CodeQL command failed with exit code ${LASTEXITCODE}: $CodeqlExe $($args -join ' ')"
    }
}

Set-Location $RepoRoot
New-Item -ItemType Directory -Force -Path $CodeqlRoot | Out-Null

Remove-CodeqlPath -Path $DatabasePath
Remove-CodeqlPath -Path $SourcePath
New-Item -ItemType Directory -Force -Path $SourcePath | Out-Null

$files = git ls-files --cached --modified --others --exclude-standard | Where-Object {
    $_ -notlike ".ai/*" -and
    $_ -notlike ".codeql/*" -and
    (Test-Path -LiteralPath (Join-Path $RepoRoot $_) -PathType Leaf)
}

foreach ($file in $files) {
    $destination = Join-Path $SourcePath $file
    $destinationDirectory = Split-Path -Parent $destination
    New-Item -ItemType Directory -Force -Path $destinationDirectory | Out-Null
    Copy-Item -LiteralPath (Join-Path $RepoRoot $file) -Destination $destination -Force
}

Invoke-Codeql pack download "codeql/python-queries@$QueryPackVersion"

if (-not $Suite) {
    $packageRoot = Join-Path $env:USERPROFILE ".codeql/packages/codeql/python-queries/$QueryPackVersion"
    $Suite = Join-Path $packageRoot "codeql-suites/python-security-and-quality.qls"
}
if (-not (Test-Path -LiteralPath $Suite -PathType Leaf)) {
    throw "CodeQL query suite not found: $Suite"
}

Invoke-Codeql database create $DatabasePath --language=python --build-mode=none --source-root $SourcePath
Invoke-Codeql database analyze $DatabasePath $Suite --format=sarif-latest --output=$SarifPath

function Test-ExplicitCodeqlSuppression {
    param($Result)

    $location = $Result.locations[0].physicalLocation
    $relativePath = $location.artifactLocation.uri -replace '/', [IO.Path]::DirectorySeparatorChar
    $sourceFile = [IO.Path]::GetFullPath((Join-Path $SourcePath $relativePath))
    $sourceRoot = [IO.Path]::GetFullPath($SourcePath) + [IO.Path]::DirectorySeparatorChar
    if (-not $sourceFile.StartsWith($sourceRoot, [StringComparison]::OrdinalIgnoreCase)) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $sourceFile -PathType Leaf)) {
        return $false
    }

    $lines = @(Get-Content -LiteralPath $sourceFile)
    $lineIndex = [int]$location.region.startLine - 1
    $markers = @("codeql[$($Result.ruleId)]", "lgtm[$($Result.ruleId)]")
    foreach ($candidateIndex in @($lineIndex, ($lineIndex - 1))) {
        if ($candidateIndex -lt 0 -or $candidateIndex -ge $lines.Count) { continue }
        foreach ($marker in $markers) {
            if ($lines[$candidateIndex].Contains($marker)) { return $true }
        }
    }
    return $false
}

$allResults = @((Get-Content -LiteralPath $SarifPath -Raw | ConvertFrom-Json).runs[0].results)
$suppressedResults = @($allResults | Where-Object { Test-ExplicitCodeqlSuppression $_ })
$results = @($allResults | Where-Object { -not (Test-ExplicitCodeqlSuppression $_) })
if ($suppressedResults.Count -gt 0) {
    Write-Host "CodeQL accepted $($suppressedResults.Count) explicitly reviewed source suppression(s)."
}
if ($results.Count -gt 0) {
    throw "CodeQL reported $($results.Count) finding(s). Review $SarifPath."
}

Write-Host "CodeQL completed with no unsuppressed findings. SARIF written to $SarifPath"
