param(
    [string]$Repository = "sagiistar-prog/roughcut-agent"
)

$ErrorActionPreference = "Continue"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location -LiteralPath $RepoRoot

$failures = New-Object System.Collections.Generic.List[string]
$RepoRootForGit = $RepoRoot.Replace("\", "/")

function Write-Section {
    param([string]$Title)
    Write-Host ""
    Write-Host "=== $Title ==="
}

function Run-Git {
    param([string[]]$Arguments)
    $output = & git -c "safe.directory=$RepoRootForGit" @Arguments 2>&1
    $exitCode = $LASTEXITCODE
    if ($null -ne $output) {
        $output | ForEach-Object { Write-Host $_ }
    }
    if ($exitCode -ne 0) {
        $failures.Add("git $($Arguments -join ' ') failed")
    }
    return @($output)
}

Write-Section "Git Status"
$statusOutput = Run-Git @("status", "--short", "--branch")
$statusLines = @($statusOutput | Where-Object { $_ -and ($_ -notmatch "^## ") })
if ($statusLines.Count -gt 0) {
    foreach ($line in $statusLines) {
        $failures.Add("Working tree is not clean: $line")
    }
}

Write-Section "Git Remote"
Run-Git @("remote", "-v") | Out-Null

Write-Section "Recent Commits"
Run-Git @("log", "--oneline", "-5") | Out-Null

Write-Section "GitHub Visibility"
$githubPublic = $false
$ghOutput = & gh repo view $Repository --json nameWithOwner,visibility,url 2>&1
$ghExit = $LASTEXITCODE
if ($ghExit -eq 0) {
    $ghText = ($ghOutput | Out-String).Trim()
    Write-Host $ghText
    try {
        $ghJson = $ghText | ConvertFrom-Json
        if ($ghJson.visibility -eq "PUBLIC") {
            $githubPublic = $true
        } else {
            $failures.Add("GitHub repository is not PUBLIC: $($ghJson.visibility)")
        }
    } catch {
        $failures.Add("Could not parse gh repo view JSON output")
    }
} else {
    Write-Host "gh repo view failed; falling back to curl status check."
    $ghOutput | ForEach-Object { Write-Host $_ }
    $url = "https://github.com/$Repository"
    $statusCode = (& curl.exe -L -o NUL -s -w "%{http_code}" $url 2>&1 | Out-String).Trim()
    Write-Host "curl status: $statusCode $url"
    if ($statusCode -eq "200") {
        $githubPublic = $true
    } else {
        $failures.Add("GitHub repository page is not publicly reachable by curl, status=$statusCode")
    }
}

Write-Section "Tracked Files Audit"
$trackedFiles = @(& git -c "safe.directory=$RepoRootForGit" ls-files 2>&1)
if ($LASTEXITCODE -ne 0) {
    $trackedFiles | ForEach-Object { Write-Host $_ }
    $failures.Add("git ls-files failed")
    $trackedFiles = @()
}
Write-Host "Tracked files: $($trackedFiles.Count)"

$blockedDirs = @("raw", "work", "output", ".venv", "raw_duplicates_quarantine")
$blockedExts = @(".mp4", ".mov", ".mkv", ".avi", ".wav", ".mp3", ".m4a")
foreach ($file in $trackedFiles) {
    $normalized = $file.Replace("\", "/")
    $segments = @($normalized -split "/")
    foreach ($dir in $blockedDirs) {
        if ($segments -contains $dir) {
            $failures.Add("Forbidden tracked directory item: $file")
        }
    }
    $ext = [System.IO.Path]::GetExtension($file).ToLowerInvariant()
    if ($blockedExts -contains $ext) {
        $failures.Add("Forbidden tracked media file: $file")
    }
}

Write-Section "Large Tracked Files"
foreach ($file in $trackedFiles) {
    $fullPath = Join-Path $RepoRoot $file
    if (Test-Path -LiteralPath $fullPath -PathType Leaf) {
        $size = (Get-Item -LiteralPath $fullPath).Length
        if ($size -gt 1MB) {
            $failures.Add("Tracked file larger than 1MB: $file ($size bytes)")
            Write-Host "$file $size bytes"
        }
    }
}

Write-Section "Sensitive Text Scan"
$textExtensions = @(".md", ".txt", ".csv", ".yaml", ".yml", ".py", ".ps1", ".json", ".toml", ".ini", ".gitignore", "")
$sensitivePatterns = @(
    @{ Label = "Windows user directory marker"; Pattern = ("C:" + "\" + "Users"); Mode = "literal" },
    @{ Label = "local username marker"; Pattern = ("Sagi" + "istariam"); Mode = "literal" },
    @{ Label = "old workspace marker"; Pattern = ("Documents" + "\" + "New project 2"); Mode = "literal" },
    @{ Label = "local project directory marker"; Pattern = ("Downloads" + "\" + "roughcut-agent"); Mode = "literal" },
    @{ Label = "GitHub classic token prefix"; Pattern = ("ghp" + "_"); Mode = "literal" },
    @{ Label = "GitHub fine-grained token prefix"; Pattern = ("github" + "_pat_"); Mode = "literal" },
    @{ Label = "Anthropic token env marker"; Pattern = ("ANTHROPIC" + "_AUTH" + "_TOKEN"); Mode = "literal" },
    @{ Label = "API token prefix marker"; Pattern = (("(^|[^A-Za-z])") + "sk" + "-[A-Za-z0-9]"); Mode = "regex" }
)
foreach ($file in $trackedFiles) {
    $ext = [System.IO.Path]::GetExtension($file).ToLowerInvariant()
    if ($textExtensions -notcontains $ext) {
        continue
    }
    $fullPath = Join-Path $RepoRoot $file
    if (-not (Test-Path -LiteralPath $fullPath -PathType Leaf)) {
        continue
    }
    try {
        $content = [System.IO.File]::ReadAllText($fullPath, [System.Text.Encoding]::UTF8)
    } catch {
        continue
    }
    foreach ($item in $sensitivePatterns) {
        $matched = $false
        if ($item.Mode -eq "regex") {
            $matched = [System.Text.RegularExpressions.Regex]::IsMatch($content, $item.Pattern, [System.Text.RegularExpressions.RegexOptions]::IgnoreCase)
        } else {
            $matched = $content.IndexOf($item.Pattern, [System.StringComparison]::OrdinalIgnoreCase) -ge 0
        }
        if ($matched) {
            $failures.Add("Sensitive text found in ${file}: $($item.Label)")
        }
    }
}

Write-Section "Conclusion"
if ($failures.Count -eq 0 -and $githubPublic) {
    Write-Host "PASS"
    exit 0
}

Write-Host "FAIL"
foreach ($failure in $failures) {
    Write-Host "- $failure"
}
exit 1