# -*- coding: utf-8 -*-
"""验证 curl_cffi 自定义 JA3 精确复现目标指纹，然后直发搜索接口"""
import socket, threading, time, sys
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from ja3_from_pcap import parse_client_hello
from curl_cffi import requests as cr

# 抖音业务接口 Cronet 主栈（pcap 实证，GREASE 已剔除）
JA3_STR = ("771,4865-4866-4867-49195-49199-49196-49200-52393-52392-49171-49172-156-157-47-53,"
           "0-23-65281-10-11-35-16-5-13-18-51-45-43-27-17513-21,29-23-24,0")
TARGET_HASH = "cd08e31494f9531f560d64c695473da9"

cap = {}


def srv():
    s = socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("127.0.0.1", 0)); s.listen(1)
    cap["port"] = s.getsockname()[1]
    c, _ = s.accept(); c.settimeout(2)
    d = b""
    try:
        while len(d) < 8192:
            x = c.recv(8192)
            if not x:
                break
            d += x
            if len(d) >= 5:
                rl = int.from_bytes(d[3:5], "big")
                if len(d) >= 5 + rl:
                    break
    except socket.timeout:
        pass
    c.close(); s.close()
    cap["data"] = d


t = threading.Thread(target=srv); t.start(); time.sleep(0.3)
try:
    cr.get(f"https://127.0.0.1:{cap['port']}/", ja3=JA3_STR, verify=False, timeout=4)
except Exception as e:
    pass
t.join(5)
r = parse_client_hello(cap.get("data", b""))
if r:
    ja3, h, sni, det = r
    print("自定义 JA3 复现:", h)
    print("目标 JA3      :", TARGET_HASH)
    print("MATCH" if h == TARGET_HASH else "MISMATCH")
    print("exts:", ",".join(det["exts"]))
else:
    print("parse fail, head:", cap.get("data", b"")[:16].hex())
