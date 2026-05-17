$ErrorActionPreference = "Stop"

Write-Host "=== AI Guard: Install Git Hooks ===" -ForegroundColor Cyan

$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

if (-not (Test-Path ".githooks")) {
    New-Item -ItemType Directory -Path ".githooks" | Out-Null
}

$hookPath = Join-Path ".githooks" "pre-push"
if (-not (Test-Path $hookPath)) {
    Write-Host "[ERROR] Missing hook file: $hookPath" -ForegroundColor Red
    exit 1
}

git config core.hooksPath .githooks

Write-Host "[OK] Git hooks installed: core.hooksPath=.githooks" -ForegroundColor Green
Write-Host "[OK] pre-push will run scripts/ai-guard/check-before-push.ps1 before git push." -ForegroundColor Green
Write-Host "" 
Write-Host "To test manually:" -ForegroundColor Cyan
Write-Host "  pwsh ./scripts/ai-guard/check-before-push.ps1 -FailOnWarnings"
