# Shared publishing helpers, also exercised against disposable local repositories.
function Invoke-Git {
    & git --no-pager @args
    if ($LASTEXITCODE -ne 0) { throw "git $($args -join ' ') failed (exit $LASTEXITCODE)." }
}

function Sync-RemoteMain {
    & git show-ref --verify --quiet refs/remotes/origin/main
    if ($LASTEXITCODE -eq 1) { return $false }
    if ($LASTEXITCODE -ne 0) { throw 'Could not inspect origin/main.' }
    $behind = Invoke-Git rev-list --count HEAD..origin/main
    if ([int]$behind -eq 0) { return $false }

    Write-Host "Integrating $behind upstream commit(s) before pushing..."
    & git --no-pager merge --no-edit origin/main | Out-Host
    if ($LASTEXITCODE -ne 0) {
        $mergeMarker = Invoke-Git rev-parse --git-path MERGE_HEAD
        if (Test-Path -LiteralPath $mergeMarker) {
            Invoke-Git merge --abort | Out-Host
        }
        throw 'GitHub changes overlap with your local changes. Your work is safely committed locally and the merge was cancelled. Ask Codex to resolve the overlap, then rerun this launcher. Nothing was pushed.'
    }
    return $true
}
