[CmdletBinding()]
param(
    [string]$Message,
    [switch]$CheckOnly
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
. (Join-Path $PSScriptRoot 'publish-github-lib.ps1')
$transcriptStarted = $false
$logPath = Join-Path (Get-Location) '.codex-local\publish-github.log'

function Invoke-PublishChecks {
    Write-Host 'Checking lint and building the local static site...'
    if (-not (Test-Path node_modules)) {
        & npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
    $savedBasePath = $env:NEXT_PUBLIC_BASE_PATH
    try {
        $env:NEXT_PUBLIC_BASE_PATH = ''
        & npm.cmd run check
        if ($LASTEXITCODE -ne 0) { throw 'Validation failed. Fix the errors before publishing.' }
        if (Get-Command python -ErrorAction SilentlyContinue) {
            & python -m scripts.validate.validate_prototype_outputs
            if ($LASTEXITCODE -ne 0) { throw 'Saved data validation failed. Nothing was pushed.' }
        }
    } finally {
        $env:NEXT_PUBLIC_BASE_PATH = $savedBasePath
    }
}

try {
    New-Item -ItemType Directory -Force (Split-Path -Parent $logPath) | Out-Null
    Start-Transcript -LiteralPath $logPath -Append | Out-Null
    $transcriptStarted = $true
    Write-Host "Publisher log: $logPath"
    foreach ($command in @('git', 'node', 'npm.cmd')) {
        if (-not (Get-Command $command -ErrorAction SilentlyContinue)) {
            throw "Install $command and reopen this launcher. Git for Windows and Node.js 22 LTS are required."
        }
    }
    $branch = Invoke-Git branch --show-current
    if ($branch -ne 'main') { throw "Switch to main before publishing. Current branch: $branch" }
    foreach ($marker in @('MERGE_HEAD', 'rebase-merge', 'rebase-apply', 'CHERRY_PICK_HEAD')) {
        $markerPath = Invoke-Git rev-parse --git-path $marker
        if (Test-Path -LiteralPath $markerPath) { throw 'Finish the current merge, rebase, or cherry-pick before publishing.' }
    }
    if (Invoke-Git diff --name-only --diff-filter=U) { throw 'Resolve Git conflicts before publishing.' }

    Invoke-PublishChecks
    if ($CheckOnly) {
        Write-Host 'Checks passed. No files were staged, committed, or pushed.'
        exit 0
    }

    $remoteUrl = Invoke-Git config --get remote.origin.url
    if ($remoteUrl -notmatch '^https://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$' -and
        $remoteUrl -notmatch '^git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$') {
        throw 'Configure origin with this project''s GitHub repository URL first. See README.md.'
    }
    $repoOwner = $Matches[1]
    $repoName = $Matches[2]
    Write-Host "Publishing to $remoteUrl"
    foreach ($key in @('user.name', 'user.email')) {
        $value = Invoke-Git config --get $key
        if (-not $value) { throw "Set your Git identity first: git config $key YOUR_VALUE" }
    }

    Invoke-Git fetch origin

    Write-Host 'Including all new, modified, and deleted files except Git-ignored files:'
    Invoke-Git status --short
    Invoke-Git add --all
    $stagedFiles = Invoke-Git diff --cached --name-only --diff-filter=ACMR
    foreach ($file in $stagedFiles) {
        if ($file -match '^(data/(archives|restored|raw)/|\.codex-local/|out/|\.next/)' -or
            ($file -match '(^|/)\.env($|\.)' -and $file -ne '.env.example')) {
            throw "Private or generated local-only files must not be published: $file"
        }
        $item = Get-Item -LiteralPath $file
        if ($item.Length -ge 100MB) { throw "GitHub cannot accept this file: $file. Ask Codex to move or exclude it." }
    }
    & git diff --cached --quiet
    $diffResult = $LASTEXITCODE
    if ($diffResult -eq 1) {
        Write-Host ''
        Write-Host 'Changes ready for this commit:'
        Invoke-Git diff --cached --shortstat
        if (-not $Message) {
            Write-Host ''
            Write-Host 'Enter a short description, for example: Add adaptive legends to county maps'
            $Message = Read-Host 'Commit description (Enter for an automatic dated message)'
        }
        if ([string]::IsNullOrWhiteSpace($Message)) {
            $Message = 'Update PolicyWatch ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
        }
        Invoke-Git commit -m $Message
    } elseif ($diffResult -eq 0) {
        Write-Host 'No file changes to commit. Pushing any existing local commits.'
    } else {
        throw 'Could not inspect staged changes.'
    }
    $integrated = Sync-RemoteMain
    if ($integrated) {
        Write-Host 'Checking the integrated version before pushing...'
        Invoke-PublishChecks
    }
    Invoke-Git push --set-upstream origin main
    Write-Host ''
    Write-Host 'Push succeeded. GitHub Actions will deploy new commits; deployment takes a few minutes.'
    Write-Host "Deployment status: https://github.com/$repoOwner/$repoName/actions"
    $siteUrl = "https://$repoOwner.github.io/"
    if ($repoName -ine "$repoOwner.github.io") { $siteUrl += "$repoName/" }
    Write-Host "GitHub Pages: $siteUrl"
} catch {
    Write-Host "ERROR: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
} finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
