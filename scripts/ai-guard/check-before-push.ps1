param(
    [switch]$FailOnWarnings
)

$ErrorActionPreference = "Stop"

Write-Host "=== AI Guard: Pre Push Check ===" -ForegroundColor Cyan

$repoRoot = git rev-parse --show-toplevel
Set-Location $repoRoot

# ============================================================
# 1. 必須ファイルの存在確認
# ============================================================
$requiredFiles = @(
    "CLAUDE.md",
    ".claude/rules/10-known-mistakes.md",
    ".claude/rules/20-pre-push-checklist.md",
    "docs/ai-lessons/MISTAKE_LOG.md"
)

$hasError = $false
$warnings  = @()

Write-Host "`n[1] Required files"
foreach ($file in $requiredFiles) {
    if (-not (Test-Path $file)) {
        Write-Host "  [ERROR] Missing: $file" -ForegroundColor Red
        $hasError = $true
    } else {
        Write-Host "  [OK]    $file"
    }
}

# ============================================================
# 2. 変更ファイル一覧
# ============================================================
Write-Host "`n[2] Changed files"
$changedFiles = (git diff --name-only) -split "`n" | Where-Object { $_ }
$stagedFiles  = (git diff --cached --name-only) -split "`n" | Where-Object { $_ }

if ($changedFiles) {
    Write-Host "  Unstaged:"
    $changedFiles | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "  Unstaged: (none)"
}

if ($stagedFiles) {
    Write-Host "  Staged:"
    $stagedFiles | ForEach-Object { Write-Host "    $_" }
} else {
    Write-Host "  Staged: (none)"
}

# ============================================================
# 3. 禁止パターンチェック（KM との照合）
# ============================================================
Write-Host "`n[3] Forbidden file patterns (KM-0001, KM-0002)"
$forbiddenPatterns = @(
    @{ pattern = "\.tmp$";       label = "temp file" },
    @{ pattern = "\.log$";       label = "log file" },
    @{ pattern = "__pycache__";  label = "Python cache" },
    @{ pattern = "node_modules"; label = "node_modules" },
    @{ pattern = "\.env$";       label = ".env file (secrets!)" },
    @{ pattern = "\.DS_Store$";  label = "macOS metadata" }
)

$allChanged = (@() + $changedFiles + $stagedFiles) | Where-Object { $_ }

foreach ($file in $allChanged) {
    foreach ($fp in $forbiddenPatterns) {
        if ($file -match $fp.pattern) {
            $warnings += "Suspicious file included: $file ($($fp.label))"
        }
    }
}

if ($warnings.Count -eq 0) {
    Write-Host "  [OK] No forbidden files detected"
}

# ============================================================
# 4. Python requirements チェック (KM-0001, KM-0002, KM-0003)
# ============================================================
Write-Host "`n[4] Python requirements check (KM-0001/0002/0003)"
$reqFiles = Get-ChildItem -Recurse -Filter "requirements.txt" -ErrorAction SilentlyContinue

foreach ($req in $reqFiles) {
    $lines = Get-Content $req.FullName | Where-Object { $_ -notmatch "^\s*#" -and $_ -match "\S" }
    $stdLibNames = @("hashlib", "hashlib2", "os", "sys", "json", "time", "datetime",
                     "re", "collections", "functools", "itertools", "pathlib", "typing")
    foreach ($line in $lines) {
        $pkgName = ($line -split "==|>=|<=|~=|>|<")[0].Trim()
        if ($stdLibNames -contains $pkgName) {
            $warnings += "Possible stdlib in requirements: $pkgName in $($req.FullName)"
        }
    }

    # functions-framework が必要な Dockerfile があるか確認
    $dockerfilePath = Join-Path $req.DirectoryName "Dockerfile"
    if (Test-Path $dockerfilePath) {
        $dockerfile = Get-Content $dockerfilePath -Raw
        if ($dockerfile -match "functions.framework" -and (Get-Content $req.FullName) -notmatch "functions.framework") {
            $warnings += "Dockerfile uses functions_framework but not in $($req.FullName)"
        }
    }
}

if ($warnings.Count -eq 0) {
    Write-Host "  [OK] No obvious requirements issues"
}

# ============================================================
# 5. Cloud Build secretEnv チェック (KM-0011)
# ============================================================
Write-Host "`n[5] Cloud Build secretEnv check (KM-0011)"
$cloudbuildFiles = Get-ChildItem -Recurse -Filter "cloudbuild.yaml" -ErrorAction SilentlyContinue

foreach ($cb in $cloudbuildFiles) {
    $content = Get-Content $cb.FullName -Raw
    # $$VAR を使っているのに secretEnv がない step を粗く検出
    if ($content -match "\$\$\w+" -and $content -notmatch "secretEnv") {
        $warnings += "cloudbuild.yaml uses \$\$VAR but no secretEnv found: $($cb.FullName)"
    }
}

if ($warnings.Count -eq 0) {
    Write-Host "  [OK] No Cloud Build secretEnv issues detected"
}

# ============================================================
# 6. Supabase migration DROP PUBLICATION チェック (KM-0014)
# ============================================================
Write-Host "`n[6] Migration safety check (KM-0014)"
$migFiles = Get-ChildItem -Recurse -Filter "*.sql" -ErrorAction SilentlyContinue

foreach ($mig in $migFiles) {
    $content = Get-Content $mig.FullName -Raw
    if ($content -match "DROP\s+PUBLICATION") {
        $warnings += "Dangerous DROP PUBLICATION in migration: $($mig.FullName) (KM-0014)"
    }
}

if ($warnings.Count -eq 0) {
    Write-Host "  [OK] No DROP PUBLICATION in migrations"
}

# ============================================================
# 7. 結果サマリー
# ============================================================
Write-Host "`n=== Summary ==="
if ($warnings.Count -gt 0) {
    Write-Host "`nWarnings:" -ForegroundColor Yellow
    foreach ($w in $warnings) {
        Write-Host "  [WARN] $w" -ForegroundColor Yellow
    }
}

if ($hasError) {
    Write-Host "`n[FAILED] Pre push check failed. Fix errors above." -ForegroundColor Red
    exit 1
}

if ($FailOnWarnings -and $warnings.Count -gt 0) {
    Write-Host "`n[FAILED] Pre push check failed due to warnings." -ForegroundColor Red
    exit 1
}

if ($warnings.Count -gt 0) {
    Write-Host "`n[PASSED with warnings] Review warnings before pushing." -ForegroundColor Yellow
} else {
    Write-Host "`n[PASSED] Pre push check completed successfully." -ForegroundColor Green
}

exit 0
