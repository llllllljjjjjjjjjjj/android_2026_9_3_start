$log='D:\reserve_agent\android\_archive\tmp_c_drive_scan\vmware_cleanup.log'
$script:lines=@()
function Log([string]$m){ $script:lines += $m }
try { sc.exe delete VMnetDHCP | Out-Null; Log 'DEL_SERVICE VMnetDHCP' } catch { Log "FAIL VMnetDHCP : $_" }
try { sc.exe delete 'VMware NAT Service' | Out-Null; Log 'DEL_SERVICE VMware NAT Service' } catch { Log "FAIL VMware NAT Service : $_" }
foreach($d in 'C:\Program Files (x86)\VMware','C:\ProgramData\VMware'){
  if(Test-Path -LiteralPath $d){ try{ Remove-Item -LiteralPath $d -Recurse -Force -ErrorAction Stop; Log "DEL_DIR $d" }catch{ Log "FAIL_DIR $d : $($_.Exception.Message)" } } else { Log "SKIP_DIR $d" }
}
$msiexec=Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'msiexec.exe' }
if($msiexec){ foreach($m in $msiexec){ try{ Stop-Process -Id $m.ProcessId -Force -ErrorAction Stop; Log "KILL_MSIEXEC $($m.ProcessId)" }catch{ Log "FAIL_KILL $($m.ProcessId)" } } } else { Log 'NO_MSIEXEC' }
[System.IO.File]::WriteAllLines($log,$script:lines)
