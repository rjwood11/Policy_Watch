# Integration checks use local disposable repositories, never GitHub.
$ErrorActionPreference = 'Stop'
. (Join-Path (Split-Path -Parent $PSScriptRoot) 'publish-github-lib.ps1')
$project = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$fixture = Join-Path $project ('.codex-local\publisher-test-' + [guid]::NewGuid().ToString('N'))
$savedLocation = Get-Location

function Assert-True($Condition, [string]$Message) {
    if (-not $Condition) { throw $Message }
}

try {
    New-Item -ItemType Directory -Path $fixture | Out-Null
    $remote = Join-Path $fixture 'remote.git'
    $upstream = Join-Path $fixture 'upstream'
    $local = Join-Path $fixture 'local'
    Invoke-Git init --bare $remote | Out-Host
    Invoke-Git init --initial-branch=main $upstream | Out-Host
    Set-Location $upstream
    Invoke-Git config user.name 'Publisher test'
    Invoke-Git config user.email 'publisher-test@example.invalid'
    Set-Content shared.txt 'base'
    Invoke-Git add --all
    Invoke-Git commit -m 'Base fixture' | Out-Host
    Invoke-Git remote add origin $remote
    Invoke-Git push --set-upstream origin main | Out-Host
    Invoke-Git clone --branch main $remote $local | Out-Host
    Set-Location $local
    Invoke-Git config user.name 'Publisher test'
    Invoke-Git config user.email 'publisher-test@example.invalid'

    Set-Location $upstream
    Set-Content remote.txt 'remote update'
    Invoke-Git add --all
    Invoke-Git commit -m 'Remote update' | Out-Host
    Invoke-Git push | Out-Host
    Set-Location $local
    Invoke-Git fetch origin | Out-Host
    Assert-True (Sync-RemoteMain) 'Expected fast-forward integration.'
    Assert-True (Test-Path remote.txt) 'Missing fast-forwarded file.'

    Set-Content owner.txt 'owner work'
    Invoke-Git add --all
    Invoke-Git commit -m 'Owner work' | Out-Host
    Set-Location $upstream
    Set-Content second-remote.txt 'another remote update'
    Invoke-Git add --all
    Invoke-Git commit -m 'Independent remote update' | Out-Host
    Invoke-Git push | Out-Host
    Set-Location $local
    Invoke-Git fetch origin | Out-Host
    Assert-True (Sync-RemoteMain) 'Expected non-conflicting merge.'
    Assert-True ((Test-Path owner.txt) -and (Test-Path second-remote.txt)) 'A merge lost local or remote work.'

    Set-Content shared.txt 'owner version'
    Invoke-Git add --all
    Invoke-Git commit -m 'Conflicting owner work' | Out-Host
    $savedHead = Invoke-Git rev-parse HEAD
    Set-Location $upstream
    Set-Content shared.txt 'remote version'
    Invoke-Git add --all
    Invoke-Git commit -m 'Conflicting remote work' | Out-Host
    Invoke-Git push | Out-Host
    Set-Location $local
    Invoke-Git fetch origin | Out-Host
    $stopped = $false
    try { Sync-RemoteMain | Out-Null } catch {
        if ($_.Exception.Message -notmatch 'overlap') { throw }
        $stopped = $true
    }
    Assert-True $stopped 'Expected the publisher to stop on conflicting edits.'
    Assert-True ((Invoke-Git rev-parse HEAD) -eq $savedHead) 'The owner commit changed during conflict recovery.'
    Assert-True ((Get-Content shared.txt) -eq 'owner version') 'Conflict recovery did not retain owner work.'
    Assert-True (-not (Test-Path (Invoke-Git rev-parse --git-path MERGE_HEAD))) 'A merge was left unfinished.'
    Write-Host 'Publisher checks passed: fast-forward, independent merge, and safe conflict recovery.'
} finally {
    Set-Location $savedLocation
}
