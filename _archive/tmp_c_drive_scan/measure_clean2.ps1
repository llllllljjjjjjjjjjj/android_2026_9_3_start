$targets = [ordered]@{
    'PackageCache'            = 'C:\ProgramData\Package Cache'
    'Gradle_caches'           = 'C:\Users\lenovo\.gradle\caches'
    'dot_cache'               = 'C:\Users\lenovo\.cache'
    'npm_cache'               = 'C:\Users\lenovo\AppData\Local\npm-cache'
    'miniconda_pkgs'          = 'C:\Users\lenovo\miniconda3\pkgs'
    'pip_cache'               = 'C:\Users\lenovo\AppData\Local\pip'
    'Playwright_browsers'     = 'C:\Users\lenovo\AppData\Local\ms-playwright'
    'LocalAppData_Temp'       = 'C:\Users\lenovo\AppData\Local\Temp'
    'RecycleBin'              = 'C:\$Recycle.Bin'
    'Claude_dir'              = 'C:\Users\lenovo\.claude'
    'DSH_dir'                 = 'C:\Users\lenovo\.dsh'
    'C_tmp_chrome'            = 'C:\temp'
    'pnpm_cache'              = 'C:\Users\lenovo\AppData\Local\pnpm-cache'
    'Everything'              = 'C:\Users\lenovo\AppData\Local\Everything'
    'CrashDumps'              = 'C:\Users\lenovo\AppData\Local\CrashDumps'
    'M2_repo'                 = 'C:\Users\lenovo\.m2\repository'
    'AdsPower_cache'          = 'C:\.ADSPOWER_GLOBAL\cache'
    'NuGet_cache'             = 'C:\Users\lenovo\AppData\Local\NuGet'
    'leidian9_docs'           = 'C:\Users\lenovo\Documents\leidian9'
    'WinUpdate_download'      = 'C:\Windows\SoftwareDistribution\Download'
    'KuGou_Temp'              = 'C:\KuGou\Temp'
    'mitmproxy'               = 'C:\Users\lenovo\.mitmproxy'
    'AVD'                     = 'C:\Users\lenovo\.android\avd'
}

function Get-SizeBytes([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) { return -1 }
    $o = robocopy $p 'C:\__robocopy_null__' /L /S /NP /NJH /NFL /NDL /BYTES /R:0 /W:0 2>&1
    $bytesLine = $o | Select-String -Pattern '^\s*Bytes\s*:' | Select-Object -Last 1
    if (-not $bytesLine) { return -2 }
    $toks = ($bytesLine.ToString().Trim() -split '\s+')
    if ($toks.Count -lt 3) { return -2 }
    $v = $toks[2] -replace '[^\d]',''
    if ($v -eq '') { return -2 }
    return [double]$v
}

$rows = foreach ($k in $targets.Keys) {
    $b = Get-SizeBytes $targets[$k]
    $note = switch ($b) { -1 {'MISSING'} -2 {'PARSE_ERR'} default {'OK'} }
    [pscustomobject]@{ Target=$k; Path=$targets[$k]; Bytes=$b; GB=if($b -ge 0){[math]::Round($b/1GB,2)}else{0}; Note=$note }
}
$rows | Sort-Object Bytes -Descending | Format-Table Target,GB,Note,Path -AutoSize | Out-String -Width 200
$rows | Export-Csv -LiteralPath 'D:\reserve_agent\android\_archive\tmp_c_drive_scan\clean_sizes2.csv' -NoTypeInformation -Encoding UTF8
Write-Output 'DONE'
