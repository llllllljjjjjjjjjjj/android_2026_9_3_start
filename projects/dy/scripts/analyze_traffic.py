# -*- coding: utf-8 -*-
"""分析搜索流量 pcap: 协议分布 / 连接对端 / ClientHello SNI / 搜索链路"""
import sys, struct
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
from ja3_from_pcap import parse_pcap, parse_client_hello

path = r"D:\reserve_agent\android\projects\dy\capture\search_traffic.pcap"
pkts = parse_pcap(path)
print("packets:", len(pkts))


def parse_l3(pkt):
    """返回 (proto, ip_src, ip_dst, l4_off, total_len, l2) 支持 Ethernet/SLL"""
    # Ethernet
    if len(pkt) >= 14 and pkt[12:14] == b"\x08\x00":
        return _ip(pkt, 14)
    # Linux cooked v1 (16B): type2 arphrd2 addrlen2 addr8 proto2
    if len(pkt) >= 16 and pkt[14:16] == b"\x08\x00":
        return _ip(pkt, 16)
    return None


def _ip(pkt, off):
    ip = pkt[off:]
    if len(ip) < 20 or (ip[0] >> 4) != 4:
        return None
    ihl = (ip[0] & 0x0f) * 4
    proto = ip[9]
    total = struct.unpack(">H", ip[2:4])[0]
    src = ".".join(str(b) for b in ip[12:16])
    dst = ".".join(str(b) for b in ip[16:20])
    return proto, src, dst, off + ihl, total


udp_conns, tcp_conns, sni_map = {}, {}, {}
hello_count = 0
for pkt in pkts:
    r = parse_l3(pkt)
    if not r:
        continue
    proto, src, dst, l4, total = r
    l4data = pkt[l4:total + (l4 - (0 if l4 < 20 else 0))] if False else pkt[l4:]
    if proto == 17 and len(l4data) >= 8:  # UDP
        sp, dp = struct.unpack(">HH", l4data[:4])
        key = (dst, dp)
        udp_conns[key] = udp_conns.get(key, 0) + 1
    elif proto == 6 and len(l4data) >= 20:  # TCP
        sp, dp = struct.unpack(">HH", l4data[:4])
        doff = (l4data[12] >> 4) * 4
        if len(l4data) < doff:
            continue
        payload = l4data[doff:]
        key = (dst, dp)
        tcp_conns[key] = tcp_conns.get(key, 0) + 1
        if payload[:1] == b"\x16":
            ch = parse_client_hello(payload)
            if ch:
                hello_count += 1
                _, h, sni, det = ch
                sni_map.setdefault((dst, dp), set()).add((sni, h))

print("\n=== UDP 对端（端口, 包数）===")
for (dst, dp), n in sorted(udp_conns.items(), key=lambda x: -x[1])[:15]:
    print(f"  {dst}:{dp}  {n}pkt")

print("\n=== TCP 对端（端口, 包数）===")
for (dst, dp), n in sorted(tcp_conns.items(), key=lambda x: -x[1])[:20]:
    print(f"  {dst}:{dp}  {n}pkt")

print("\n=== ClientHello SNI（%d 个）===" % hello_count)
for (dst, dp), vs in sorted(sni_map.items()):
    for sni, h in vs:
        print(f"  {dst}:{dp}  SNI={sni}  JA3={h}")
