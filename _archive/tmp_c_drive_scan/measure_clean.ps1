$targets = [ordered]@{
    'KuGou_tp2p'              = 'C:\KuGou\Temp\tp2p'
    'C_tmp_chrome'            = 'C:\temp'
    'AdsPower_cache'          = 'C:\.ADSPOWER_GLOBAL\cache'
    'Gradle_caches'           = 'C:\Users\lenovo\.gradle\caches'
    'npm_cache'               = 'C:\Users\lenovo\AppData\Local\npm-cache'
    'pnpm_cache'              = 'C:\Users\lenovo\AppData\Local\pnpm-cache'
    'pip_cache'               = 'C:\Users\lenovo\AppData\Local\pip'
    'NuGet_cache'             = 'C:\Users\lenovo\AppData\Local\NuGet'
    'M2_repo'                 = 'C:\Users\lenovo\.m2\repository'
    'dot_cache'               = 'C:\Users\lenovo\.cache'
    'WinUpdate_download'      = 'C:\Windows\SoftwareDistribution\Download'
    'LocalAppData_Temp'       = 'C:\Users\lenovo\AppData\Local\Temp'
    'Windows_Temp'            = 'C:\Windows\Temp'
    'CbsTemp'                 = 'C:\Windows\CbsTemp'
    'Prefetch'                = 'C:\Windows\prefetch'
    'RecycleBin'              = 'C:\$Recycle.Bin'
    'leidian9_docs'           = 'C:\Users\lenovo\Documents\leidian9'
    'leidian14_docs'          = 'C:\Users\lenovo\Documents\leidian14'
    'miniconda_pkgs'          = 'C:\Users\lenovo\miniconda3\pkgs'
    'conda_cache'             = 'C:\Users\lenovo\.conda'
    'Claude_dir'              = 'C:\Users\lenovo\.claude'
    'DSH_dir'                 = 'C:\Users\lenovo\.dsh'
    'AVD'                     = 'C:\Users\lenovo\.android\avd'
    'PackageCache'            = 'C:\ProgramData\Package Cache'
    'mitmproxy'               = 'C:\Users\lenovo\.mitmproxy'
    'Playwright_browsers'     = 'C:\Users\lenovo\AppData\Local\ms-playwright'
    'Everything'              = 'C:\Users\lenovo\AppData\Local\Everything'
    'CrashDumps'              = 'C:\Users\lenovo\AppData\Local\CrashDumps'
    'Bytedance'               = 'C:\Users\lenovo\AppData\Local\Bytedance'
}

function Get-DirSizeGB([string]$p) {
    if (-not (Test-Path -LiteralPath $p)) { return [pscustomobject]@{Path=$p; GB=[double]0; Note='MISSING'} }
    $o = robocopy $p 'C:\__robocopy_null__' /L /S /NP /NJH /NFL /NDL /BYTES /R:0 /W:0 2>&1 | Out-String
    $m = [regex]::Match($o, 'Bytes\s*:\s*([\d\s]+)')
    if (-not $m.Success) { return [pscustomobject]@{Path=$p; GB=[double]0; Note='ERR'} }
    $bytes = [double]($m.Groups[1].Value -replace '\s','')
    return [pscustomobject]@{Path=$p; GB=[math]::Round($bytes/1GB,2); Note='OK'}
}

$results = foreach ($k in $targets.Keys) {
    $r = Get-DirSizeGB $targets[$k]
    [pscustomobject]@{Target=$k; Path=$r.Path; GB=$r.GB; Note=$r.Note}
}
$results | Sort-Object GB -Descending | Format-Table -AutoSize | Out-String -Width 200
$results | Export-Csv -LiteralPath 'D:\reserve_agent\android\_archive\tmp_c_drive_scan\clean_sizes.csv' -NoTypeInformation -Encoding UTF8
Write-Output 'DONE'
