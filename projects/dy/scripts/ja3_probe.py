# -*- coding: utf-8 -*-
"""JA3 探针: 本地 socket 收 curl_cffi 的原始 ClientHello，计算 JA3 并与目标对比"""
import socket, threading, sys, os
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from ja3_from_pcap import parse_client_hello
from curl_cffi import requests as cr

TARGET = "cd08e31494f9531f560d64c695473da9"   # 抖音业务接口 Cronet 主栈
TARGETS = ["chrome110", "chrome116", "chrome119", "chrome120", "chrome123",
           "chrome124", "chrome131", "chrome131_android", "chrome133a", "chrome136"]

captured = {}


def server_once(port_holder):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    srv.listen(1)
    port_holder.append(srv.getsockname()[1])
    conn, _ = srv.accept()
    conn.settimeout(2)
    data = b""
    try:
        while len(data) < 4096:
            chunk = conn.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) > 5 and len(data) >= 5 + int.from_bytes(data[3:5], "big") + 0:
                # 收到完整 record 即停
                rec_len = int.from_bytes(data[3:5], "big")
                if len(data) >= 5 + rec_len:
                    break
    except socket.timeout:
        pass
    conn.close()
    srv.close()
    captured["data"] = data


for name in TARGETS:
    port_holder = []
    t = threading.Thread(target=server_once, args=(port_holder,))
    t.start()
    import time
    time.sleep(0.3)
    port = port_holder[0]
    try:
        cr.get(f"https://127.0.0.1:{port}/", impersonate=name, verify=False, timeout=4)
    except Exception:
        pass
    t.join(timeout=5)
    data = captured.pop("data", b"")
    r = parse_client_hello(data)
    if not r:
        print(f"{name:18s} PARSE_FAIL ({len(data)}B) head={data[:8].hex()}")
        continue
    ja3, h, sni, det = r
    match = " ★★★ MATCH" if h == TARGET else ""
    print(f"{name:18s} JA3={h}{match}")
    print(f"{'':18s}  ciphers({len(det['ciphers'])})={','.join(det['ciphers'])}")
    print(f"{'':18s}  exts({len(det['exts'])})={','.join(det['exts'])}")
    print(f"{'':18s}  curves={','.join(det['curves'])} fmt={','.join(det['formats'])}")
