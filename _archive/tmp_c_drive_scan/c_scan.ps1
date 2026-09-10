$ErrorActionPreference = 'SilentlyContinue'
$out = 'D:\reserve_agent\android\_archive\tmp_c_drive_scan\c_drive_tree.txt'
$sb = New-Object System.Collections.Generic.List[string]
$script:count = 0
$script:cap = 60000

function Emit([string]$text) {
    if ($script:count -ge $script:cap) { return }
    $sb.Add($text)
    $script:count++
}

function Scan-Dir {
    param(
        [string]$Path,
        [int]$Depth,
        [int]$MaxDepth
    )
    if ($script:count -ge $script:cap) { return }
    if ($Depth -gt $MaxDepth) { return }
    $indent = '    ' * ($Depth - 1)
    $name = Split-Path $Path -Leaf
    if ($Depth -eq 0) { $name = 'C:\' }
    Emit ("{0}[{1}] {2}" -f $indent, $Depth, $name)
    if ($Depth -ge $MaxDepth) { return }

    $dirs = @(Get-ChildItem -LiteralPath $Path -Directory -Force |
        Where-Object { $_.Attributes -notmatch 'ReparsePoint' } |
        Sort-Object Name)
    foreach ($d in $dirs) {
        if ($script:count -ge $script:cap) { return }
        Scan-Dir -Path $d.FullName -Depth ($Depth + 1) -MaxDepth $MaxDepth
    }
}

# System-ish roots: only list immediate children (they are OS-internal, labelled later)
$sysRoots = @('Windows', 'Program Files', 'Program Files (x86)', 'ProgramData', 'Recovery', 'System Volume Information', '$Recycle.Bin', 'Documents and Settings', '$SysReset', 'inetpub')
$top = @(Get-ChildItem -LiteralPath 'C:\' -Directory -Force | Sort-Object Name)

foreach ($item in $top) {
    if ($script:count -ge $script:cap) { break }
    $isSys = $sysRoots -contains $item.Name
    if ($isSys) {
        Scan-Dir -Path $item.FullName -Depth 1 -MaxDepth 2
    } else {
        # user-facing / app roots get depth 6
        Scan-Dir -Path $item.FullName -Depth 1 -MaxDepth 6
    }
}

# Top-level files worth noting
$files = @(Get-ChildItem -LiteralPath 'C:\' -File -Force | Sort-Object Name)
Emit '[FILES]'
foreach ($f in $files) {
    if ($script:count -ge $script:cap) { break }
    $sz = if ($f.Length -gt 1MB) { '{0} MB' -f [math]::Round($f.Length / 1MB, 1) } elseif ($f.Length -gt 1KB) { '{0} KB' -f [math]::Round($f.Length / 1KB, 1) } else { '{0} B' -f $f.Length }
    Emit ('    {0}  ({1})' -f $f.Name, $sz)
}

if ($script:count -ge $script:cap) { $sb.Add('...TRUNCATED AT LINE CAP...') }
[System.IO.File]::WriteAllLines($out, $sb, (New-Object System.Text.UTF8Encoding($false)))
Write-Output ("lines={0} out={1}" -f $sb.Count, $out)
