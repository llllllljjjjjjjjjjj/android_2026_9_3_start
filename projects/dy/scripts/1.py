import frida, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]          # projects/dy/scripts/1.py → 项目根
ADB = str(ROOT / "android_mcp" / "toolchain" / "bin" / "windows" / "platform-tools" / "adb.exe")
HOOK = str(ROOT / "projects" / "dy" / "hooks" / "dy_hook21.js")

subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])   # frida-server 经 adb 转发（幂等）
pids = subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()
if not pids:
    print("app not running"); sys.exit(1)
pid = int(pids[0])
d = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
s = d.attach(pid)                                  # ⚠️ 必须 pid 直连（App 反枚举）
sc = s.create_script(open(HOOK, encoding="utf-8").read())
sc.load()

url = "https://log0-misc-lf.amemv.com/service/2/app_log/?aid=1128&device_id=2310516478094584&tt_data=a"
hdr = "cookie\r\npassport_csrf_token=441f7e5260f91551c264fe7e4ac152d8\r\nuser-agent\r\ncom.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001)"
out = sc.exports_sync.oracle(url, hdr)             # ⚠️ 方法名必须全小写
print(out)   # X-Argus\r\n...X-Gorgon\r\n...X-Medusa\r\n...
