$ErrorActionPreference = 'SilentlyContinue'
$out = 'D:\reserve_agent\android\_archive\tmp_c_drive_scan\c_drive_tree_clean.txt'
$sb = New-Object System.Collections.Generic.List[string]
$script:count = 0
$script:cap = 30000

function Emit([string]$text) {
    if ($script:count -ge $script:cap) { return }
    $sb.Add($text)
    $script:count++
}

function Is-NoiseName([string]$n) {
    if ($n -match '^[0-9a-fA-F]{32}$') { return $true }
    if ($n -match '^[0-9a-fA-F]{40}$') { return $true }
    if ($n -match '^[0-9a-fA-F-]{36}$') { return $true }
    if ($n -match '^[0-9a-fA-F]{8}$') { return $true }
    if ($n -match '^(\.)?\d{4,}$') { return $true }
    return $false
}

function Scan-Dir {
    param(
        [string]$Path,
        [int]$Depth,
        [int]$MaxDepth,
        [string]$Prefix
    )
    if ($script:count -ge $script:cap) { return }
    if ($Depth -gt $MaxDepth) { return }
    $name = Split-Path $Path -Leaf
    if ($Depth -eq 1) { $name = Split-Path (Split-Path $Path -Parent) -Leaf + '\' + $name }
    $indent = '    ' * ($Depth - 1)
    Emit ("{0}{1}[{2}] {3}" -f $indent, $Prefix, $Depth, $name)
    if ($Depth -ge $MaxDepth) { return }

    $dirs = @(Get-ChildItem -LiteralPath $Path -Directory -Force |
        Where-Object { $_.Attributes -notmatch 'ReparsePoint' } |
        Sort-Object Name)

    # Fold pure-noise subtrees: if every child is a noise name, print a count line only.
    if ($dirs.Count -gt 0) {
        $noise = @($dirs | Where-Object { Is-NoiseName $_.Name })
        if ($noise.Count -eq $dirs.Count -and $dirs.Count -ge 5) {
            Emit ("{0}        ... ({1} 个无意义哈希/编号目录，已折叠)" -f ('    ' * $Depth))
            return
        }
    }
    foreach ($d in $dirs) {
        if ($script:count -ge $script:cap) { return }
        if (Is-NoiseName $d.Name) {
            # print single collapsed child heading with no further walk
            Emit ("{0}{1}[{2}] {3}  (...)" -f ('    ' * $Depth), $Prefix, ($Depth + 1), $d.Name)
            continue
        }
        Scan-Dir -Path $d.FullName -Depth ($Depth + 1) -MaxDepth $MaxDepth -Prefix ''
    }
}

$sysRoots = @('Windows', 'Program Files', 'Program Files (x86)', 'ProgramData', 'Recovery', 'System Volume Information', '$Recycle.Bin', 'Documents and Settings', '$SysReset', 'inetpub')
$top = @(Get-ChildItem -LiteralPath 'C:\' -Directory -Force | Sort-Object Name)

foreach ($item in $top) {
    if ($script:count -ge $script:cap) { break }
    $isSys = $sysRoots -contains $item.Name
    $max = if ($isSys) { 2 } else { 6 }
    Scan-Dir -Path $item.FullName -Depth 1 -MaxDepth $max -Prefix ''
}

Emit '[顶层文件]'
$files = @(Get-ChildItem -LiteralPath 'C:\' -File -Force | Sort-Object Name)
foreach ($f in $files) {
    if ($script:count -ge $script:cap) { break }
    $sz = if ($f.Length -gt 1MB) { '{0} MB' -f [math]::Round($f.Length / 1MB, 1) } elseif ($f.Length -gt 1KB) { '{0} KB' -f [math]::Round($f.Length / 1KB, 1) } else { '{0} B' -f $f.Length }
    Emit ('    {0}  ({1})' -f $f.Name, $sz)
}

if ($script:count -ge $script:cap) { $sb.Add('...TRUNCATED...') }
[System.IO.File]::WriteAllText($out, ($sb -join "`n") + "`n", (New-Object System.Text.UTF8Encoding($true)))
Write-Output ("lines={0}" -f $sb.Count)
