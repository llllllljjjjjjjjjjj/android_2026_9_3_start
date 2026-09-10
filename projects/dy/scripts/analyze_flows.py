# -*- coding: utf-8 -*-
"""TCP 流重组: 定位搜索 POST（~15KB 上行）连接 + 解析其 ClientHello（跨段）"""
import sys, struct
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from ja3_from_pcap import parse_pcap, parse_client_hello

path = r"D:\reserve_agent\android\projects\dy\capture\search_traffic.pcap"
pkts = parse_pcap(path)
DEV = "172.24.137.31"
flows = {}  # (dst,dport) -> {"up":b"", "down":n, "pkts":n, "seq_start"}


def parse_l3(pkt):
    if len(pkt) >= 14 and pkt[12:14] == b"\x08\x00":
        return _ip(pkt, 14)
    if len(pkt) >= 16 and pkt[14:16] == b"\x08\x00":
        return _ip(pkt, 16)
    return None


def _ip(pkt, off):
    ip = pkt[off:]
    if len(ip) < 20 or (ip[0] >> 4) != 4:
        return None
    ihl = (ip[0] & 0x0f) * 4
    return ip[9], ".".join(str(b) for b in ip[12:16]), ".".join(str(b) for b in ip[16:20]), off + ihl, struct.unpack(">H", ip[2:4])[0]


for pkt in pkts:
    r = parse_l3(pkt)
    if not r or r[0] != 6:
        continue
    proto, src, dst, l4, total = r
    tcp = pkt[l4:]
    if len(tcp) < 20:
        continue
    sp, dp = struct.unpack(">HH", tcp[:4])
    seq = struct.unpack(">I", tcp[4:8])[0]
    doff = (tcp[12] >> 4) * 4
    payload = tcp[doff:]
    if not payload:
        continue
    if src == DEV:  # 上行
        key = (dst, dp)
        f = flows.setdefault(key, {"up": b"", "up_pkts": 0, "down": 0})
        f["up"] += payload  # 粗略拼接（同窗口内顺序基本一致）
        f["up_pkts"] += 1
    else:  # 下行
        key = (src, sp)
        f = flows.setdefault(key, {"up": b"", "up_pkts": 0, "down": 0})
        f["down"] += len(payload)

print("=== 上行流量排序（找 ~15KB 搜索 POST）===")
for (dst, dp), f in sorted(flows.items(), key=lambda x: -len(x[1]["up"])):
    up = f["up"]
    if len(up) < 20:
        continue
    is_tls = up[0] == 0x16
    ch = parse_client_hello(up) if is_tls else None
    sni = ch[2] if ch else None
    ja3 = ch[1] if ch else None
    print(f"{dst}:{dp} up={len(up)}B ({f['up_pkts']}pkt) down={f['down']}B TLS={is_tls} SNI={sni} JA3={ja3}")
    # 打印上行前 40 字节 hex（判断协议）
    print("    head:", up[:40].hex())
