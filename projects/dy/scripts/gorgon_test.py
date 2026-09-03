# -*- coding: utf-8 -*-
# gorgon_test.py — X-Gorgon 单参数实验: 同 url 连调 3 次 + query 单字符变化
# 前置: 设备已连 + 抖音运行中 + frida-server f1657 已起
import time
import frida
import subprocess

ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook21.js"
# headers 必须非空（G5 实测: 空串 → 28065c 返回 NULL）；内容对 Gorgon 无影响
BASE_HDR = "cookie\r\npassport_csrf_token=441f7e5260f91551c264fe7e4ac152d8\r\nuser-agent\r\ncom.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001)\r\naccept-encoding\r\ngzip, deflate, br"

def get_pid_via_adb():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    out = subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().strip()
    if not out:
        raise RuntimeError("pidof empty: 抖音没在运行")
    return int(out.split()[0])

def parse_pairs(s):
    # oracle 输出 "name\r\nvalue\r\n..." → dict
    parts = s.split("\r\n")
    d = {}
    for i in range(0, len(parts) - 1, 2):
        d[parts[i]] = parts[i + 1]
    return d

def main():
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = get_pid_via_adb()
    print("[*] pid=%d attach..." % pid)
    session = dev.attach(pid)
    with open(HOOK, "r", encoding="utf-8") as f:
        js = f.read()
    script = session.create_script(js)
    script.load()
    time.sleep(2)
    print("[*] metasec base =", script.exports_sync.getbase())

    URL = "https://log0-misc-lf.amemv.com/service/2/app_log/performance/p2/?aid=1128&device_id=2310516478094584"

    # 实验 A: 同 url 连调 3 次（间隔 <0.5s，应同上下文）
    for i in range(3):
        out = script.exports_sync.oracle(URL, BASE_HDR)
        print("[A%d raw] %s" % (i, repr(out)[:100]))
        g = parse_pairs(out).get("X-Gorgon", "N/A")
        print("[A%d] %s" % (i, g))

    # 实验 B: query 改一个字符（device_id 末位 4→5）
    out = script.exports_sync.oracle(
        URL.replace("device_id=2310516478094584", "device_id=2310516478094585"), BASE_HDR)
    g = parse_pairs(out).get("X-Gorgon", "N/A")
    print("[B1] %s" % g)

    session.detach()

if __name__ == "__main__":
    main()
