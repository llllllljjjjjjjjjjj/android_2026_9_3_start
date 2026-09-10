# -*- coding: utf-8 -*-
"""tcpdump 抓搜索时刻底层流量: 协议/端口/对端 IP/SNI"""
import subprocess, time, os, sys

ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUT = r"D:\reserve_agent\android\projects\dy\capture\search_traffic.pcap"
KW = sys.argv[1] if len(sys.argv) > 1 else "太阳"
from urllib.parse import quote


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


# 清理旧抓包 + 后台启动 tcpdump（抓 443 全部 TCP/UDP）
adb("shell", "su -c 'pkill tcpdump; rm -f /data/local/tmp/st.pcap'")
time.sleep(1)
adb("shell", "su -c 'nohup tcpdump -i any -s 0 -w /data/local/tmp/st.pcap tcp or udp >/dev/null 2>&1 &'")
print("[*] tcpdump started")
time.sleep(2)

# 清场 + 触发搜索
adb("shell", "input", "keyevent", "3")
time.sleep(2)
adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
    "-d", "snssdk1128://search?keyword=%s" % quote(KW))
print("[*] 搜索已触发, 抓 14s...")
time.sleep(14)

adb("shell", "su -c 'pkill -SIGINT tcpdump'")
time.sleep(2)
print(adb("shell", "su -c 'ls -la /data/local/tmp/st.pcap'").stdout)
r = adb("pull", "/data/local/tmp/st.pcap", OUT)
print(r.stdout, r.stderr)
print("[*] ->", OUT, os.path.getsize(OUT) if os.path.exists(OUT) else "MISSING")
