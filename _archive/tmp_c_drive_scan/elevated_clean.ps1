$ErrorActionPreference='Continue'
$log='D:\reserve_agent\android\_archive\tmp_c_drive_scan\elevated_clean.log'
$lines=@()
function Do-Remove([string]$p){
  if(Test-Path -LiteralPath $p){
    try{ Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Stop; $lines += "OK   $p" }
    catch{ $lines += "FAIL $p : $($_.Exception.Message)" }
  } else { $lines += "SKIP $p" }
}
Do-Remove 'C:\leidian'
Do-Remove 'C:\Program Files\Oray'
Do-Remove 'C:\Program Files\JetBrains'
Do-Remove 'C:\Program Files\Rockstar Games'
Do-Remove 'C:\Program Files\TechChangeLife'
Do-Remove 'C:\ProgramData\Oray'
Do-Remove 'C:\ProgramData\OrayClient'
Do-Remove 'C:\Users\lenovo\AppData\Local\LocalAIAssistant'
Do-Remove 'C:\Users\lenovo\Desktop\此电脑\PyCharm 2020.1.3 x64.lnk'
Do-Remove 'C:\Users\lenovo\Desktop\此电脑\科技改变生活.lnk'
Do-Remove 'C:\Users\lenovo\Desktop\此电脑\腾讯会议.lnk'
Do-Remove 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\有道云笔记.lnk'
Do-Remove 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\腾讯会议'
Do-Remove 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\小熊猫C++'
Do-Remove 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\无畏契约'
Do-Remove 'C:\ProgramData\Microsoft\Windows\Start Menu\Programs\LocalAIAssistant'
# Fix AdsPower startup shortcut target (old AdsPower.exe -> AdsPower Global.exe)
$ads='C:\ProgramData\Microsoft\Windows\Start Menu\Programs\Startup\AdsPower.lnk'
if(Test-Path -LiteralPath $ads){
  try{
    $sh=New-Object -ComObject WScript.Shell
    $sc=$sh.CreateShortcut($ads)
    $sc.TargetPath='D:\AdsPower Global\AdsPower Global.exe'
    $sc.Save()
    $lines += "FIXED AdsPower.lnk -> AdsPower Global.exe"
  } catch { $lines += "FAIL AdsPower.lnk fix : $($_.Exception.Message)" }
}
[System.IO.File]::WriteAllLines($log,$lines,[System.Text.Encoding]::UTF8)
