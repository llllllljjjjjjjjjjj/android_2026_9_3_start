# -*- coding: utf-8 -*-
"""IPv4+IPv6 全协议分析: 找搜索 POST 走的协议族（重点 IPv6 UDP/443 QUIC）"""
import sys, struct
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from ja3_from_pcap import parse_pcap, parse_client_hello

path = r"D:\reserve_agent\android\projects\dy\capture\search_traffic.pcap"
pkts = parse_pcap(path)
DEV4 = "172.24.137.31"
DEV6_PREFIX = "2409:8938:ce6:270c"

stats = {"v4_tcp": {}, "v4_udp": {}, "v6_tcp": {}, "v6_udp": {}}
flows_up = {}


def parse_l3(pkt):
    # Ethernet
    if len(pkt) >= 14:
        et = pkt[12:14]
        if et == b"\x08\x00":
            return 4, _v4(pkt, 14)
        if et == b"\x86\xdd":
            return 6, _v6(pkt, 14)
    # SLL
    if len(pkt) >= 16:
        et = pkt[14:16]
        if et == b"\x08\x00":
            return 4, _v4(pkt, 16)
        if et == b"\x86\xdd":
            return 6, _v6(pkt, 16)
    return None, None


def _v4(pkt, off):
    ip = pkt[off:]
    ihl = (ip[0] & 0x0f) * 4
    return ip[9], ".".join(str(b) for b in ip[12:16]), ".".join(str(b) for b in ip[16:20]), off + ihl, struct.unpack(">H", ip[2:4])[0]


def _v6(pkt, off):
    ip = pkt[off:]
    nh = ip[6]
    plen = struct.unpack(">H", ip[4:6])[0]
    src = socket_inet6(ip[8:24]); dst = socket_inet6(ip[24:40])
    p = 40
    # 跳过常见扩展头
    while nh in (0, 43, 44, 50, 51, 60):
        nh = ip[p]; hlen = (ip[p + 1] + 1) * 8; p += hlen
    return nh, src, dst, off + p, off + 40 + plen


def socket_inet6(b):
    import ipaddress
    return str(ipaddress.IPv6Address(b))


for pkt in pkts:
    r = parse_l3(pkt)
    if not r or not r[1]:
        continue
    ver, l3 = r
    proto, src, dst, l4, total = l3
    seg = pkt[l4:]
    if proto == 17 and len(seg) >= 8:
        sp, dp = struct.unpack(">HH", seg[:4])
        ulen = struct.unpack(">H", seg[4:6])[0]
        key = ("v%d_udp" % ver, dst, dp)
        d = stats[key[0]]
        d[key[1:]] = d.get(key[1:], 0) + max(0, ulen - 8)
        if src.startswith(DEV6_PREFIX) or src == DEV4:
            f = flows_up.setdefault((ver, "udp", dst, dp), {"up": 0, "n": 0})
            f["up"] += len(seg[8:]); f["n"] += 1
    elif proto == 6 and len(seg) >= 20:
        sp, dp = struct.unpack(">HH", seg[:4])
        doff = (seg[12] >> 4) * 4
        payload = seg[doff:]
        key = ("v%d_tcp" % ver, dst, dp)
        d = stats[key[0]]
        d[key[1:]] = d.get(key[1:], 0) + len(payload)
        if src.startswith(DEV6_PREFIX) or src == DEV4:
            f = flows_up.setdefault((ver, "tcp", dst, dp), {"up": b"", "n": 0})
            if isinstance(f["up"], bytes):
                f["up"] += payload
            f["n"] += 1

for fam in ("v4_udp", "v6_udp", "v4_tcp", "v6_tcp"):
    print(f"=== {fam} 对端（按字节）===")
    items = sorted(stats[fam].items(), key=lambda x: -x[1])[:12]
    for (dst, dp), n in items:
        print(f"  {dst}:{dp}  {n}B")
    print()

print("=== 设备上行流（找搜索 POST）===")
for k, f in sorted(flows_up.items(), key=lambda x: -(len(x[1]["up"]) if isinstance(x[1]["up"], bytes) else x[1]["up"]))[:15]:
    ver, pr, dst, dp = k
    up = f["up"]
    if isinstance(up, bytes):
        print(f"  v{ver} {pr} {dst}:{dp} up={len(up)}B {f['n']}pkt head={up[:12].hex()}")
    else:
        print(f"  v{ver} {pr} {dst}:{dp} up={up}B {f['n']}pkt")
