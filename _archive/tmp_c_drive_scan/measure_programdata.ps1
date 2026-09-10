$root='C:\ProgramData'
$dirs = @(Get-ChildItem -LiteralPath $root -Directory -Force | Sort-Object Name)
function Get-SizeMB([string]$p) {
    $o = robocopy $p 'C:\__robocopy_null__' /L /S /NP /NJH /NFL /NDL /BYTES /R:0 /W:0 2>&1
    $bytesLine = $o | Select-String -Pattern '^\s*Bytes\s*:' | Select-Object -Last 1
    if (-not $bytesLine) { return -1 }
    $toks = ($bytesLine.ToString().Trim() -split '\s+')
    if ($toks.Count -lt 3) { return -1 }
    $v = $toks[2] -replace '[^\d]',''
    if ($v -eq '') { return -1 }
    return [math]::Round(([double]$v/1MB),1)
}
$rows = foreach($d in $dirs){
    $mb = Get-SizeMB $d.FullName
    $samples = @(Get-ChildItem -LiteralPath $d.FullName -Force -ErrorAction SilentlyContinue | Select-Object -First 5 | ForEach-Object { $_.Name })
    [pscustomobject]@{ Name=$d.Name; SizeMB=$mb; Samples=($samples -join ' | ') }
}
$rows | Sort-Object SizeMB -Descending | Format-Table Name,SizeMB,Samples -Wrap -AutoSize | Out-String -Width 220
$rows | Export-Csv -LiteralPath 'D:\reserve_agent\android\_archive\tmp_c_drive_scan\programdata_sizes.csv' -NoTypeInformation -Encoding UTF8
Write-Output 'DONE'
