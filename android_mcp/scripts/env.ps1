# env.ps1 - Portable toolchain environment for DSH pwsh sessions (ASCII only)
#
# Dot-source it to add jadx / apktool / bundled adb to PATH and set the
# ANDROID_MCP_* variables used by the MCP servers and skills:
#
#   . .\android_mcp\scripts\env.ps1
#
# Idempotent: PATH entries and env vars are only set when missing.

$ErrorActionPreference = "SilentlyContinue"

# android_mcp\scripts\env.ps1 -> 上级 android_mcp -> 项目根
$Root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)

$toolDirs = @(
    (Join-Path $Root "tools\jadx\bin"),
    (Join-Path $Root "tools\apktool"),
    (Join-Path $Root "android_mcp\toolchain\bin\windows\platform-tools"),
    (Join-Path $Root "android_mcp\toolchain\python\vendor")
)

foreach ($d in $toolDirs) {
    if (Test-Path $d) {
        if ($env:PATH -notlike "*$d*") { $env:PATH = "$d;$env:PATH" }
    }
}

if (-not $env:ANDROID_MCP_PROJECT_ROOT)         { $env:ANDROID_MCP_PROJECT_ROOT = $Root }
if (-not $env:ANDROID_MCP_ALLOW_EMULATOR)       { $env:ANDROID_MCP_ALLOW_EMULATOR = "0" }
if (-not $env:ANDROID_MCP_FRIDA_DEVICE)         { $env:ANDROID_MCP_FRIDA_DEVICE = "9C181EC3BF7E0D" }
if (-not $env:ANDROID_MCP_REMOTE_PATCHED_FRIDA) { $env:ANDROID_MCP_REMOTE_PATCHED_FRIDA = "/data/local/tmp/florida-server" }

Write-Host "[env] DSH portable toolchain ready - root: $Root"
Write-Host "[env] jadx / apktool / adb on PATH; ANDROID_MCP_* set (see AGENTS.md for baseline)"
