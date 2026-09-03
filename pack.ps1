# pack.ps1 - Package the whole portable kit (including projects/) to a destination
#
# Usage:
#   & .\pack.ps1 -Destination D:\work\reverse-kit          # full kit
#   & .\pack.ps1 -Destination D:\work\reverse-kit -NoVenv  # skip the big frida venvs
#   & .\pack.ps1 -Destination D:\work\reverse-kit -Legacy  # also copy 11111/ leftovers
#
# Excluded by default: __pycache__, .venv-* (optional), 11111/ (old duplicate).

param(
    [Parameter(Mandatory = $true)][string]$Destination,
    [switch]$NoVenv,
    [switch]$Legacy
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot   # pack.ps1 lives at the project root

if (-not $Destination) { throw "-Destination is required" }
$Dst = if ([System.IO.Path]::IsPathRooted($Destination)) { $Destination } else { Join-Path (Get-Location) $Destination }

function Copy-Dir([string]$src, [string]$dst, [string[]]$excludeDirs = @("__pycache__")) {
    if (-not (Test-Path $src)) { Write-Host "skip (missing): $src"; return }
    $xd = @("/XD"); foreach ($e in $excludeDirs) { $xd += $e }
    & robocopy $src $dst /E $xd /NFL /NDL /NJH /NJS /NC /NS
    if ($LASTEXITCODE -gt 7) { throw "robocopy failed: $src" }
}

Write-Host "Packing portable kit -> $Dst"
New-Item -ItemType Directory -Path $Dst -Force | Out-Null

# Config layer (.dsh contains skills/mcp/tools/scripts)
Copy-Dir (Join-Path $Root ".dsh") (Join-Path $Dst ".dsh")

# MCP servers + toolchain
Copy-Dir (Join-Path $Root "android_mcp") (Join-Path $Dst "android_mcp")

# Reverse tools
Copy-Dir (Join-Path $Root "tools") (Join-Path $Dst "tools")

# Projects (copied verbatim)
Copy-Dir (Join-Path $Root "projects") (Join-Path $Dst "projects")

# Workflow instruction file (from .dsh, so the packed root is self-contained)
Copy-Item (Join-Path $Root ".dsh\AGENTS.md") (Join-Path $Dst "AGENTS.md") -Force

# Frida venvs (optional)
if (-not $NoVenv) {
    Copy-Dir (Join-Path $Root ".venv-frida-16.5.7")  (Join-Path $Dst ".venv-frida-16.5.7")
    Copy-Dir (Join-Path $Root ".venv-frida-16.7.19") (Join-Path $Dst ".venv-frida-16.7.19")
} else {
    Write-Host "skip venvs (-NoVenv)"
}

# Legacy leftovers (optional)
if ($Legacy -and (Test-Path (Join-Path $Root "11111"))) {
    Copy-Dir (Join-Path $Root "11111") (Join-Path $Dst "11111")
}

Write-Host ""
Write-Host "Done. On the target machine:"
Write-Host "  1) verify per AGENTS.md sec 7.2 check-path (files in place + functional verification)"
Write-Host "  2) restart DSH; skills are auto-discovered from .dsh\skills."
