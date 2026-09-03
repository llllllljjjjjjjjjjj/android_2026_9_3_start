# tools/so-reverse/setup.ps1
# On-demand installer for the native .so reverse-engineering toolset.
# Modeled after an external reference layout, adapted to this machine.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1            # list only
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Radare2 -Qbdi
#   powershell -ExecutionPolicy Bypass -File .\setup.ps1 -All
#
# No switch means "list only" (safe default).

param(
    [switch]$Radare2,
    [switch]$Qbdi,
    [switch]$Ghidra,
    [switch]$Ndk,
    [switch]$Blutter,
    [switch]$Il2Cpp,
    [switch]$Linyu,
    [switch]$All
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

# registry: name -> metadata. Recommended = small, safe, high value on this machine.
$registry = [ordered]@{
    radare2 = [ordered]@{
        Recommended = $true
        Size        = '~30 MB'
        Kind        = 'zip'
        Url         = 'https://github.com/radareorg/radare2/releases/download/6.1.6/radare2-6.1.6-w64.zip'
        Dir         = 'radare2'
        Note        = 'CLI static analysis: rabin2 / r2 / rasm2 / radiff2. Complements IDA.'
    }
    qbdi    = [ordered]@{
        Recommended = $true
        Size        = '~10 MB'
        Kind        = 'manual'
        Url         = 'https://github.com/QBDI/QBDI/releases'
        Dir         = 'qbdi'
        Note        = 'arm64 Android native DBI. Fallback when Frida is detected. Download the android-AARCH64 prebuilt asset.'
    }
    ghidra  = [ordered]@{
        Recommended = $false
        Size        = '~400 MB'
        Kind        = 'manual'
        Url         = 'https://github.com/NationalSecurityAgency/ghidra/releases'
        Dir         = 'ghidra'
        Note        = 'Free headless decompiler. Needs Java 17; installed Java 26 may be too new.'
    }
    ndk     = [ordered]@{
        Recommended = $false
        Size        = '~2 GB'
        Kind        = 'zip'
        Url         = 'https://dl.google.com/android/repository/android-ndk-r26c-windows.zip'
        Dir         = 'android-ndk-r26c'
        Note        = 'llvm-readelf/nm/strings + cross compile. Only needed to build linyu or cross-compile.'
    }
    blutter = [ordered]@{
        Recommended = $false
        Size        = '~10 MB'
        Kind        = 'git'
        Url         = 'https://github.com/worawit/blutter'
        Dir         = 'blutter'
        Note        = 'Flutter libapp.so symbol recovery. Only for Flutter targets.'
    }
    il2cpp  = [ordered]@{
        Recommended = $false
        Size        = '~5 MB'
        Kind        = 'git'
        Url         = 'https://github.com/lxraa/Il2CppDumper'
        Dir         = 'il2cppdumper'
        Note        = 'Unity IL2CPP metadata dump. Only for Unity targets. Prebuilt exe also on its release page.'
    }
    linyu   = [ordered]@{
        Recommended = $false
        Size        = 'binary'
        Kind        = 'manual'
        Url         = 'https://bbs.kanxue.com/thread-135312-1.htm'
        Dir         = 'linxerunpacker'
        Note        = 'LinxerUnpacker (kanxue tool, no GitHub). Windows native unpacker. Download from kanxue thread and extract exe here.'
    }
}

function Show-List {
    'tools/so-reverse/setup.ps1 - native .so reverse toolset'
    ''
    'Recommended (small, safe, high value):'
    foreach ($k in $registry.Keys) {
        $t = $registry[$k]
        if ($t.Recommended) { '  {0,-9} {1,-9} {2}' -f $k, $t.Size, $t.Note }
    }
    ''
    'Optional / conditional:'
    foreach ($k in $registry.Keys) {
        $t = $registry[$k]
        if (-not $t.Recommended) { '  {0,-9} {1,-9} {2}' -f $k, $t.Size, $t.Note }
    }
    ''
    'Install recommended:  .\setup.ps1 -Radare2 -Qbdi'
    'Install everything:   .\setup.ps1 -All'
    ''
}

if (-not ($Radare2 -or $Qbdi -or $Ghidra -or $Ndk -or $Blutter -or $Il2Cpp -or $Linyu -or $All)) {
    Show-List
    return
}

function Install-Tool([string]$key) {
    $t = $registry[$key]
    $dest = Join-Path $root $t.Dir
    $existing = Get-ChildItem $dest -Force -ErrorAction SilentlyContinue
    if ($existing -and $existing.Count -gt 0) {
        "SKIP $key : $dest already has content (clear it first to reinstall)"
        return
    }
    "INSTALL $key ($($t.Size)) -> $dest"
    switch ($t.Kind) {
        'zip' {
            $zip = Join-Path $env:TEMP ("{0}.zip" -f $key)
            "  download: $($t.Url)"
            Invoke-WebRequest -Uri $t.Url -OutFile $zip -UseBasicParsing
            Expand-Archive -Path $zip -DestinationPath $dest -Force
            Remove-Item $zip -Force
        }
        'git' {
            "  clone: $($t.Url)"
            git clone --depth 1 $t.Url $dest
        }
        'manual' {
            "  manual download: $($t.Url)"
            "  then extract into: $dest"
        }
    }
    "DONE $key"
    ''
}

if ($All -or $Radare2) { Install-Tool 'radare2' }
if ($All -or $Qbdi)    { Install-Tool 'qbdi' }
if ($All -or $Ghidra)  { Install-Tool 'ghidra' }
if ($All -or $Ndk)     { Install-Tool 'ndk' }
if ($All -or $Blutter) { Install-Tool 'blutter' }
if ($All -or $Il2Cpp)  { Install-Tool 'il2cpp' }
if ($All -or $Linyu)   { Install-Tool 'linyu' }
