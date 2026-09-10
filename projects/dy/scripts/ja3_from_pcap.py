# -*- coding: utf-8 -*-
"""从 pcap 解析 TLS ClientHello -> JA3 + SNI（纯标准库，剔除 GREASE）"""
import sys, struct, hashlib, glob, os

# RFC 8701 GREASE 值（0x?A?A），JA3 计算前必须剔除
GREASE = {0x0A0A, 0x1A1A, 0x2A2A, 0x3A3A, 0x4A4A, 0x5A5A, 0x6A6A, 0x7A7A,
          0x8A8A, 0x9A9A, 0xAAAA, 0xBABA, 0xCACA, 0xDADA, 0xEAEA, 0xFAFA}


def is_grease(x):
    return x in GREASE


def parse_pcap(path):
    f = open(path, "rb").read()
    magic = f[:4]
    if magic == b"\xd4\xc3\xb2\xa1":
        endian = "<"
    elif magic == b"\xa1\xb2\xc3\xd4":
        endian = ">"
    else:
        print("bad magic", magic.hex())
        return []
    off = 24
    out = []
    while off + 16 <= len(f):
        ts_sec, ts_usec, incl_len, orig_len = struct.unpack(endian + "IIII", f[off:off + 16])
        off += 16
        pkt = f[off:off + incl_len]
        off += incl_len
        out.append(pkt)
    return out


def parse_client_hello(payload):
    """payload: TCP payload，解析 ClientHello，返回 (ja3_str, ja3_hash, sni, details)"""
    try:
        if len(payload) < 6 or payload[0] != 0x16:
            return None
        # TLS record: type(1)+ver(2)+len(2)
        rec_len = struct.unpack(">H", payload[3:5])[0]
        hs = payload[5:5 + rec_len]
        if not hs or hs[0] != 0x01:  # ClientHello
            return None
        # handshake: type(1)+len(3)
        hs_len = int.from_bytes(hs[1:4], "big")
        body = hs[4:4 + hs_len]
        p = 0
        ver = body[p:p + 2].hex(); p += 2
        p += 32  # random
        sid_len = body[p]; p += 1 + sid_len
        cs_len = struct.unpack(">H", body[p:p + 2])[0]; p += 2
        ciphers = [str(body[i] * 256 + body[i + 1]) for i in range(p, p + cs_len, 2)
                   if not is_grease(body[i] * 256 + body[i + 1])]
        p += cs_len
        comp_len = body[p]; p += 1 + comp_len
        ext_total = struct.unpack(">H", body[p:p + 2])[0]; p += 2
        ext_end = p + ext_total
        exts, curves, formats, sni = [], [], [], None
        while p + 4 <= ext_end:
            etype = struct.unpack(">H", body[p:p + 2])[0]
            elen = struct.unpack(">H", body[p + 2:p + 4])[0]
            edata = body[p + 4:p + 4 + elen]
            p += 4 + elen
            if is_grease(etype):
                continue
            exts.append(str(etype))
            if etype == 0x0000:  # SNI
                try:
                    # list_len(2)+type(1)+name_len(2)+name
                    nlen = struct.unpack(">H", edata[3:5])[0]
                    sni = edata[5:5 + nlen].decode("utf-8", "ignore")
                except Exception:
                    pass
            elif etype == 0x000a:  # supported_groups
                glen = struct.unpack(">H", edata[:2])[0]
                curves = [str(struct.unpack(">H", edata[i:i + 2])[0])
                          for i in range(2, 2 + glen, 2)
                          if not is_grease(struct.unpack(">H", edata[i:i + 2])[0])]
            elif etype == 0x000b:  # EC point formats
                flen = edata[0]
                formats = [str(b) for b in edata[1:1 + flen]]
        ja3 = ",".join([
            str(int(ver, 16)),
            "-".join(ciphers),
            "-".join(exts),
            "-".join(curves),
            "-".join(formats),
        ])
        h = hashlib.md5(ja3.encode()).hexdigest()
        return ja3, h, sni, {"ver": ver, "ciphers": ciphers, "exts": exts,
                             "curves": curves, "formats": formats}
    except Exception as e:
        return None


def iter_tcp_payloads(pkts, linktype_hint=None):
    for pkt in pkts:
        # Ethernet: 14B (dst6 src6 type2); IPv4 0x0800
        # Linux SLL: 16B
        for l2 in (14, 16):
            if len(pkt) <= l2:
                continue
            if l2 == 14 and pkt[12:14] != b"\x08\x00":
                continue
            ip = pkt[l2:]
            if len(ip) < 20 or (ip[0] >> 4) != 4:
                continue
            ihl = (ip[0] & 0x0f) * 4
            proto = ip[9]
            if proto != 6:
                break
            total = struct.unpack(">H", ip[2:4])[0]
            tcp = ip[ihl:total]
            if len(tcp) < 20:
                break
            doff = (tcp[12] >> 4) * 4
            sport = struct.unpack(">H", tcp[0:2])[0]
            payload = tcp[doff:]
            if payload:
                yield sport, payload
            break


def main():
    for path in sys.argv[1:]:
        print("=== %s ===" % os.path.basename(path))
        pkts = parse_pcap(path)
        print("packets:", len(pkts))
        seen = {}
        for sport, payload in iter_tcp_payloads(pkts):
            r = parse_client_hello(payload)
            if not r:
                continue
            ja3, h, sni, det = r
            if h not in seen:
                seen[h] = {"det": det, "snis": set(), "n": 0}
            seen[h]["n"] += 1
            if sni:
                seen[h]["snis"].add(sni)
        print("unique JA3 (GREASE-stripped):", len(seen))
        for h, v in sorted(seen.items(), key=lambda kv: -kv[1]["n"]):
            det = v["det"]
            print("  JA3:", h, "| count:", v["n"])
            print("    SNIs:", sorted(v["snis"])[:6])
            print("    ver:", det["ver"], "| ciphers(%d):" % len(det["ciphers"]),
                  ",".join(det["ciphers"]))
            print("    exts(%d):" % len(det["exts"]), ",".join(det["exts"]))
            print("    curves:", ",".join(det["curves"]), "| formats:", ",".join(det["formats"]))


if __name__ == "__main__":
    main()
