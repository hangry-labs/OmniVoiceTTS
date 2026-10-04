param(
    [string]$DryRun = "0",
    [string]$NextVersion = "",
    [string]$SkipValidation = "0"
)

$ErrorActionPreference = "Stop"

function Test-Enabled {
    param([string]$Value)
    return $Value -match '^(1|true|yes|y)$'
}

function Set-Utf8Text {
    param([string]$Path, [string]$Text)
    $resolved = (Resolve-Path -LiteralPath $Path).Path
    $encoding = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($resolved, $Text, $encoding)
}

function Convert-ToPackageVersion {
    param([string]$Version)
    if ($Version -match '^\d+\.\d+$') { return "$Version.0" }
    if ($Version -match '^\d+\.\d+\.\d+$') { return $Version }
    throw "Version '$Version' must look like 0.4 or 0.4.0."
}

function Get-NextMinorSnapshot {
    param([string]$Version)
    if ($Version -match '^(\d+)\.(\d+)(?:\.\d+)?$') {
        $major = [int]$Matches[1]
        $minor = [int]$Matches[2] + 1
        return "$major.$minor-snapshot"
    }
    throw "Cannot infer the next snapshot from '$Version'. Pass NEXT_VERSION=..."
}

function Get-VersionHistoryDockerSection {
    param(
        [string]$Version,
        [string]$AvailabilityLine,
        [string]$LineEnding,
        [bool]$Rolling = $false
    )

    $containerVersion = $Version.Replace(".", "-")
    $standardContainer = if ($Rolling) { "omnivoicetts" } else { "omnivoicetts-v$containerVersion" }
    $tinyContainer = if ($Rolling) { "omnivoicetts-tiny" } else { "omnivoicetts-v$containerVersion-tiny" }
    $standardTag = if ($Rolling) { "latest" } else { "v$Version" }
    $tinyTag = if ($Rolling) { "latest_tiny" } else { "v${Version}_tiny" }
    return @(
        $AvailabilityLine,
        "",
        "**Standard image**",
        "",
        '```bash',
        "docker run --name $standardContainer --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:$standardTag",
        '```',
        "",
        "**Tiny image**",
        "",
        '```bash',
        "docker run --name $tinyContainer --restart unless-stopped -p 7861:7861 --gpus all -e CUDA_VISIBLE_DEVICES=0 -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 -v omnivoicetts_data:/app/persistent hangrylabs/omnivoicetts:$tinyTag",
        '```'
    ) -join $LineEnding
}

function Invoke-Native {
    param([string]$Description, [scriptblock]$Action)
    & $Action
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Invoke-Step {
    param([string]$Description, [scriptblock]$Action)
    Write-Host "==> $Description"
    if (-not (Test-Enabled $DryRun)) {
        & $Action
    }
}

function Get-ProjectVersion {
    $content = Get-Content -Raw -LiteralPath "pyproject.toml"
    $match = [regex]::Match($content, '(?m)^version = "([^"]+)"(?=\r?$)')
    if (-not $match.Success) {
        throw "Could not read [project].version from pyproject.toml."
    }
    return $match.Groups[1].Value
}

function Set-ProjectVersion {
    param([string]$Version)
    $content = Get-Content -Raw -LiteralPath "pyproject.toml"
    $pattern = [regex]::new('(?m)^version = "[^"]+"(?=\r?$)')
    $updated = $pattern.Replace($content, "version = `"$Version`"", 1)
    if ($updated -eq $content -and (Get-ProjectVersion) -ne $Version) {
        throw "Failed to update [project].version in pyproject.toml."
    }
    Set-Utf8Text "pyproject.toml" $updated
}

function Update-ReleaseDocument {
    param(
        [string]$Path,
        [string]$OldHeading,
        [string]$NewHeading,
        [string]$OldDockerSection,
        [string]$NewDockerSection
    )
    $content = Get-Content -Raw -LiteralPath $Path
    if (-not $content.Contains($OldHeading)) {
        throw "$Path does not contain the expected heading '$OldHeading'."
    }
    $content = $content.Replace($OldHeading, $NewHeading)
    if (-not $content.Contains($OldDockerSection)) {
        throw "$Path does not contain the expected rolling Docker section."
    }
    $content = $content.Replace($OldDockerSection, $NewDockerSection)
    Set-Utf8Text $Path $content
}

function Add-NextSnapshotSection {
    param(
        [string]$Path,
        [string]$StableHeading,
        [string]$NextHeading,
        [string]$DockerSection
    )
    $content = Get-Content -Raw -LiteralPath $Path
    if ($content.Contains($NextHeading)) { return }
    $lineEnding = if ($content.Contains("`r`n")) { "`r`n" } else { "`n" }
    $stableHeadingLine = "$StableHeading$lineEnding"
    if (-not $content.Contains($stableHeadingLine)) {
        throw "$Path release heading '$StableHeading' is not followed by a line ending."
    }
    $nextSection =
        "$NextHeading$lineEnding$lineEnding" +
        "- No changes yet.$lineEnding$lineEnding" +
        "$DockerSection$lineEnding$lineEnding" +
        $stableHeadingLine
    $content = $content.Replace($stableHeadingLine, $nextSection)
    Set-Utf8Text $Path $content
}

$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

Write-Host "Release automation creates local commits and an annotated tag, then pushes them atomically."
Write-Host "Docker images are published only by GitHub Actions."

if (-not (Test-Path -LiteralPath "VERSION")) {
    throw "VERSION file is missing from the repository root."
}

$currentVersion = (Get-Content -Raw -LiteralPath "VERSION").Trim()
$versionMatch = [regex]::Match($currentVersion, '^(\d+\.\d+(?:\.\d+)?)-snapshot$')
if (-not $versionMatch.Success) {
    throw "VERSION must be a snapshot such as 0.4-snapshot or 0.4.0-snapshot. Current: '$currentVersion'"
}

$releaseDisplayVersion = $versionMatch.Groups[1].Value
$releaseVersion = Convert-ToPackageVersion $releaseDisplayVersion
$releaseTag = "v$releaseDisplayVersion"
$expectedProjectVersion = "$releaseVersion.dev0"
$projectVersion = Get-ProjectVersion

if ($projectVersion -ne $expectedProjectVersion) {
    throw "pyproject.toml version '$projectVersion' does not match VERSION '$currentVersion' (expected '$expectedProjectVersion')."
}

if ([string]::IsNullOrWhiteSpace($NextVersion)) {
    $nextSnapshotVersion = Get-NextMinorSnapshot $releaseVersion
} else {
    $nextSnapshotVersion = $NextVersion.Trim()
}

$nextMatch = [regex]::Match($nextSnapshotVersion, '^(\d+\.\d+(?:\.\d+)?)-snapshot$')
if (-not $nextMatch.Success) {
    throw "NEXT_VERSION must look like 0.4-snapshot or 0.4.0-snapshot. Current: '$nextSnapshotVersion'"
}

$nextDisplayVersion = $nextMatch.Groups[1].Value
$nextReleaseVersion = Convert-ToPackageVersion $nextDisplayVersion
if ([version]$nextReleaseVersion -le [version]$releaseVersion) {
    throw "NEXT_VERSION '$nextSnapshotVersion' must be newer than '$releaseVersion'."
}
$nextProjectVersion = "$nextReleaseVersion.dev0"

$snapshotHeading = "### v$releaseDisplayVersion Snapshot"
$stableHeading = "### $releaseTag"
$nextSnapshotHeading = "### v$nextDisplayVersion Snapshot"
$developmentImageNotice = 'The current development snapshot is published through the rolling tags from `master`:'
$stableImageNotice = "Run this release with either immutable image variant:"

foreach ($doc in @("README.md", "docs/dockerhub.md")) {
    $content = Get-Content -Raw -LiteralPath $doc
    if (-not $content.Contains($snapshotHeading)) {
        throw "$doc must contain the exact release-history heading '$snapshotHeading'."
    }
}

$branch = (git branch --show-current).Trim()
if ($LASTEXITCODE -ne 0) { throw "Could not determine the current Git branch." }
if ($branch -ne "master") { throw "Releases must run from master. Current branch: '$branch'" }

$status = git status --porcelain --untracked-files=all -- . ":(exclude).ai" ":(exclude).ai/**"
if ($LASTEXITCODE -ne 0) { throw "Could not inspect the Git working tree." }
if ($status) {
    if (Test-Enabled $DryRun) {
        Write-Warning "The real release will require a clean working tree outside .ai/."
        $status | ForEach-Object { Write-Host "  $_" }
    } else {
        throw "Working tree outside .ai/ must be clean before release. Commit or stash the listed changes first.`n$($status -join "`n")"
    }
}

if (-not (Test-Enabled $DryRun)) {
    Invoke-Native "Fetch origin/master and tags" { git fetch origin master --tags }
    $head = (git rev-parse HEAD).Trim()
    $originMaster = (git rev-parse refs/remotes/origin/master).Trim()
    if ($head -ne $originMaster) {
        throw "master must be synchronized with origin/master before release. HEAD=$head origin/master=$originMaster"
    }
}

if (git tag --list $releaseTag) { throw "Tag $releaseTag already exists." }

Write-Host "Release version: $releaseDisplayVersion"
Write-Host "Release tag:     $releaseTag"
Write-Host "Package version: $releaseVersion"
Write-Host "Next snapshot:   $nextSnapshotVersion"
Write-Host "Next package:    $nextProjectVersion"
Write-Host "Validation:      $(if (Test-Enabled $SkipValidation) { 'skipped' } else { 'tests, lockfile, CodeQL, Dockerfile' })"

Invoke-Step "Run release validation" {
    if (-not (Test-Enabled $SkipValidation)) {
        $venvPython = Join-Path $root ".venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $venvPython)) {
            throw "Release validation requires $venvPython."
        }
        Invoke-Native "Python compilation" { & $venvPython -m compileall -q omnivoice scripts tests }
        Invoke-Native "Lightweight tests" { & $venvPython -m unittest discover -s tests -v }
        Invoke-Native "Lockfile validation" { uv lock --check }
        Invoke-Native "CodeQL analysis" { task codeql }
        Invoke-Native "Dockerfile validation" { docker build --check . }
    }
}

Invoke-Step "Update release metadata for $releaseTag" {
    Set-Utf8Text "VERSION" "$releaseDisplayVersion`n"
    Set-ProjectVersion $releaseVersion
    Invoke-Native "Refresh uv.lock for release version" { uv lock }

    foreach ($doc in @("README.md", "docs/dockerhub.md")) {
        $content = Get-Content -Raw -LiteralPath $doc
        $lineEnding = if ($content.Contains("`r`n")) { "`r`n" } else { "`n" }
        $rollingSection = Get-VersionHistoryDockerSection `
            -Version $releaseDisplayVersion `
            -AvailabilityLine $developmentImageNotice `
            -LineEnding $lineEnding `
            -Rolling $true
        $stableSection = Get-VersionHistoryDockerSection `
            -Version $releaseDisplayVersion `
            -AvailabilityLine $stableImageNotice `
            -LineEnding $lineEnding
        Update-ReleaseDocument $doc $snapshotHeading $stableHeading $rollingSection $stableSection
    }
}

Invoke-Step "Commit release metadata when needed and tag $releaseTag" {
    $releaseFiles = @("VERSION", "pyproject.toml", "uv.lock", "README.md", "docs/dockerhub.md")
    $releaseChanges = git status --porcelain -- $releaseFiles
    if ($LASTEXITCODE -ne 0) { throw "Could not inspect release metadata changes." }
    if ($releaseChanges) {
        Invoke-Native "Stage release metadata" { git add -- $releaseFiles }
        Invoke-Native "Create release commit" { git commit -m "release: $releaseTag" }
    } else {
        Write-Host "Release metadata is already committed; tagging the current HEAD."
    }
    Invoke-Native "Create annotated release tag" { git tag -a $releaseTag -m "Release $releaseTag" }
}

Invoke-Step "Prepare $nextSnapshotVersion" {
    Set-Utf8Text "VERSION" "$nextSnapshotVersion`n"
    Set-ProjectVersion $nextProjectVersion
    Invoke-Native "Refresh uv.lock for next snapshot" { uv lock }

    foreach ($doc in @("README.md", "docs/dockerhub.md")) {
        $content = Get-Content -Raw -LiteralPath $doc
        $lineEnding = if ($content.Contains("`r`n")) { "`r`n" } else { "`n" }
        $rollingSection = Get-VersionHistoryDockerSection `
            -Version $nextDisplayVersion `
            -AvailabilityLine $developmentImageNotice `
            -LineEnding $lineEnding `
            -Rolling $true
        Add-NextSnapshotSection $doc $stableHeading $nextSnapshotHeading $rollingSection
    }

    Invoke-Native "Stage next snapshot metadata" { git add -- VERSION pyproject.toml uv.lock README.md docs/dockerhub.md }
    Invoke-Native "Create next snapshot commit" { git commit -m "chore: start $nextSnapshotVersion" }
}

Invoke-Step "Push master and $releaseTag atomically" {
    Invoke-Native "Push release commits and tag" { git push --atomic origin master $releaseTag }
}

if (Test-Enabled $DryRun) {
    Write-Host "Dry run complete. No files, commits, tags, or remote refs were changed."
    Write-Host "The public GitHub Release entry remains a manual step after tagged deployment validation."
} else {
    Write-Host "Release workflow complete. master and $releaseTag were pushed atomically."
    Write-Host "GitHub Actions is responsible for publishing the release images."
    Write-Host "After validating the tagged deployment, create the public GitHub Release entry manually."
}
