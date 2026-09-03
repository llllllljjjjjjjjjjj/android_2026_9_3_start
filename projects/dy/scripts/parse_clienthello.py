# -*- coding: utf-8 -*-
"""parse_clienthello.py — 从 pcap 提取 TLS ClientHello 的 SNI + JA3/JA4 指纹。

用法: python parse_clienthello.py <pcap> [--all]
输出: 每个 ClientHello 的 src/dst、SNI、TLS 版本、cipher 数、JA3 原文 + MD5。
"""
import sys
import hashlib
import struct
from collections import OrderedDict

GREASE = {0x0a0a, 0x1a1a, 0x2a2a, 0x3a3a, 0x4a4a, 0x5a5a, 0x6a6a, 0x7a7a,
          0x8a8a, 0x9a9a, 0xaaaa, 0xbaba, 0xcaca, 0xdada, 0xeaea, 0xfafa}

def read_pcap(path):
    data = open(path, "rb").read()
    magic = data[:4]
    if magic == b"\xd4\xc3\xb2\xa1" or magic == b"\x4d\x3c\xb2\xa1":
        endian = "<"
    else:
        endian = ">"
    # global header 24 bytes
    linktype = struct.unpack(endian + "I", data[20:24])[0]
    off = 24
    pkts = []
    while off + 16 <= len(data):
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack(endian + "IIII", data[off:off+16])
        off += 16
        if off + incl_len > len(data):
            break
        pkt = data[off:off+incl_len]
        off += incl_len
        pkts.append(pkt)
    return pkts, linktype, endian

def parse_ip_tcp(pkt, linktype):
    """返回 (src_ip, dst_ip, src_port, dst_port, tcp_payload)"""
    if linktype == 1:  # Ethernet
        if len(pkt) < 14:
            return None
        eth_type = struct.unpack(">H", pkt[12:14])[0]
        off = 14
        if eth_type == 0x8100:  # VLAN
            off = 18
            eth_type = struct.unpack(">H", pkt[14:16])[0]
        if eth_type != 0x0800:
            return None
    elif linktype == 113:  # Linux cooked capture (SLL), tcpdump -i any
        if len(pkt) < 16:
            return None
        proto = struct.unpack(">H", pkt[14:16])[0]
        if proto != 0x0800:  # IPv4
            return None
        off = 16
    else:
        off = 0
    if len(pkt) < off + 20:
        return None
    ihl = (pkt[off] & 0x0f) * 4
    proto = pkt[off + 9]
    if proto != 6:  # TCP
        return None
    src_ip = ".".join(map(str, pkt[off+12:off+16]))
    dst_ip = ".".join(map(str, pkt[off+16:off+20]))
    tcp_off = off + ihl
    if len(pkt) < tcp_off + 20:
        return None
    src_port, dst_port = struct.unpack(">HH", pkt[tcp_off:tcp_off+4])
    data_off = (pkt[tcp_off+12] >> 4) * 4
    payload = pkt[tcp_off+data_off:]
    return src_ip, dst_ip, src_port, dst_port, payload

def extract_clienthellos(payload, src, dst, sport, dport):
    """从 TCP payload 提取 ClientHello（可能多个，处理 TLS record 分片）"""
    results = []
    i = 0
    while i + 5 <= len(payload):
        rtype = payload[i]
        if rtype not in (20, 21, 22, 23):
            break
        rver = struct.unpack(">H", payload[i+1:i+3])[0]
        rlen = struct.unpack(">H", payload[i+3:i+5])[0]
        if rtype == 22:
            body = payload[i+5:i+5+rlen]
            j = 0
            while j + 4 <= len(body):
                htype = body[j]
                hlen = struct.unpack(">I", b"\x00" + body[j+1:j+4])[0]
                if htype == 1:  # ClientHello
                    ch = body[j+4:j+4+hlen]
                    results.append(parse_clienthello(ch, src, dst, sport, dport))
                j += 4 + hlen
        i += 5 + rlen
    return results

def parse_clienthello(ch, src, dst, sport, dport):
    if len(ch) < 34:
        return None
    legacy_ver = struct.unpack(">H", ch[0:2])[0]
    off = 2 + 32  # legacy_version + random
    sid_len = ch[off]; off += 1
    sid = ch[off:off+sid_len]; off += sid_len
    cs_len = struct.unpack(">H", ch[off:off+2])[0]; off += 2
    ciphers = [struct.unpack(">H", ch[off+2*k:off+2*k+2])[0] for k in range(cs_len//2)]
    ciphers = [c for c in ciphers if c not in GREASE]  # 去 GREASE
    off += cs_len
    comp_len = ch[off]; off += 1
    off += comp_len
    # extensions
    ext_types = []
    curves = []
    point_fmts = []
    alpn = []
    sni = ""
    if off + 2 <= len(ch):
        ext_len = struct.unpack(">H", ch[off:off+2])[0]; off += 2
        end = off + ext_len
        while off + 4 <= end:
            etype, elen = struct.unpack(">HH", ch[off:off+4])
            edata = ch[off+4:off+4+elen]
            off += 4 + elen
            if etype in GREASE:
                continue
            ext_types.append(etype)
            if etype == 0x0000 and len(edata) >= 5:  # server_name
                # edata: list_len(2) + name_type(1) + name_len(2) + name
                try:
                    name_type = edata[2]
                    if name_type == 0:  # host_name
                        name_len = struct.unpack(">H", edata[3:5])[0]
                        sni = edata[5:5+name_len].decode("ascii", "replace")
                except Exception:
                    pass
            elif etype == 0x000a:  # supported_groups
                gl = struct.unpack(">H", edata[0:2])[0]
                curves = [struct.unpack(">H", edata[2+2*k:2+2*k+2])[0] for k in range(gl//2) if 2+2*k+2 <= len(edata)]
                curves = [c for c in curves if c not in GREASE]  # 去 GREASE
            elif etype == 0x000b:  # ec_point_formats
                pl = edata[0]
                point_fmts = list(edata[1:1+pl])
            elif etype == 0x0010:  # ALPN
                al = struct.unpack(">H", edata[0:2])[0]
                k = 2
                while k < al + 2:
                    l = edata[k]; k += 1
                    alpn.append(edata[k:k+l].decode("ascii", "replace"))
                    k += l
    ja3_str = "%d,%s,%s,%s,%s" % (
        legacy_ver,
        "-".join("%d" % c for c in ciphers),
        "-".join("%d" % e for e in ext_types),
        "-".join("%d" % c for c in curves),
        "-".join("%d" % p for p in point_fmts),
    )
    ja3 = hashlib.md5(ja3_str.encode()).hexdigest()
    return {
        "src": src, "dst": dst, "sport": sport, "dport": dport,
        "sni": sni, "legacy_ver": "0x%04x" % legacy_ver,
        "n_ciphers": len(ciphers), "n_ext": len(ext_types),
        "alpn": alpn, "ja3": ja3, "ja3_str": ja3_str,
    }

def main():
    pcap = sys.argv[1]
    show_all = "--all" in sys.argv
    pkts, linktype, endian = read_pcap(pcap)
    print("[parse] %d packets, linktype=%d endian=%s" % (len(pkts), linktype, endian))
    seen = OrderedDict()
    for pkt in pkts:
        r = parse_ip_tcp(pkt, linktype)
        if not r:
            continue
        src, dst, sport, dport, payload = r
        if not payload:
            continue
        for ch in extract_clienthellos(payload, src, dst, sport, dport):
            if not ch:
                continue
            key = ch["ja3"]
            if key not in seen:
                seen[key] = ch
    print("\n=== 唯一 ClientHello 指纹（%d 个）===" % len(seen))
    for ja3, ch in seen.items():
        print("SNI=%-40s JA3=%s  ver=%s ciphers=%d ext=%d alpn=%s" % (
            ch["sni"], ch["ja3"], ch["legacy_ver"], ch["n_ciphers"], ch["n_ext"], ch["alpn"]))
    if show_all:
        print("\n=== JA3 原文 ===")
        for ja3, ch in seen.items():
            print("SNI=%s\n  %s\n" % (ch["sni"], ch["ja3_str"]))

if __name__ == "__main__":
    main()
