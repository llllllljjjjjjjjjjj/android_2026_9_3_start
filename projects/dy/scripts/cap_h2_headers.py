# -*- coding: utf-8 -*-
"""抓 HTTP/2 请求头（含签名头）并做 HPACK 解码

流程: hook SSL_write → 收 HTTP/2 HEADERS 帧 → HPACK 静态表+动态表解码 → 还原 header
"""
import sys, time, subprocess, os, struct, json
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\cap_h2_headers.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
AID = sys.argv[1] if len(sys.argv) > 1 else "7581630849533316401"

# HPACK 静态表（RFC 7541 Appendix A，索引 1..61）
HPACK_STATIC = [
    None,
    (":authority", ""), (":method", "GET"), (":method", "POST"), (":path", "/"), (":path", "/index.html"),
    (":scheme", "http"), (":scheme", "https"), (":status", "200"), (":status", "204"), (":status", "206"),
    (":status", "304"), (":status", "400"), (":status", "404"), (":status", "500"),
    ("accept-charset", ""), ("accept-encoding", "gzip, deflate"), ("accept-language", ""),
    ("accept-ranges", ""), ("accept", ""), ("access-control-allow-origin", ""),
    ("age", ""), ("allow", ""), ("authorization", ""), ("cache-control", ""),
    ("content-disposition", ""), ("content-encoding", ""), ("content-language", ""),
    ("content-length", ""), ("content-location", ""), ("content-range", ""), ("content-type", ""),
    ("cookie", ""), ("date", ""), ("etag", ""), ("expect", ""), ("expires", ""), ("from", ""),
    ("host", ""), ("if-match", ""), ("if-modified-since", ""), ("if-none-match", ""),
    ("if-range", ""), ("if-unmodified-since", ""), ("last-modified", ""), ("link", ""),
    ("location", ""), ("max-forwards", ""), ("proxy-authenticate", ""), ("proxy-authorization", ""),
    ("range", ""), ("referer", ""), ("refresh", ""), ("retry-after", ""), ("server", ""),
    ("set-cookie", ""), ("strict-transport-security", ""), ("transfer-encoding", ""),
    ("user-agent", ""), ("vary", ""), ("via", ""), ("www-authenticate", ""),
]


def hpack_int(buf, i, prefix_bits):
    """解 HPACK 整数：prefix_bits 决定低位掩码（RFC 7541 §5.1）"""
    mask = (1 << prefix_bits) - 1
    b = buf[i]
    i += 1
    v = b & mask
    if v < mask:
        return v, i
    m = 0
    while i < len(buf):
        x = buf[i]
        i += 1
        v += (x & 0x7F) << m
        m += 7
        if not (x & 0x80):
            break
    return v, i


# HPACK Huffman 表（RFC 7541 Appendix B：256 项，每项 (code, bits)）
HUFF = [
    (0x1ff8, 13), (0x7fffd8, 23), (0xfffffe2, 28), (0xfffffe3, 28), (0xfffffe4, 28), (0xfffffe5, 28),
    (0xfffffe6, 28), (0xfffffe7, 28), (0xfffffe8, 28), (0xffffea, 24), (0x3ffffffc, 30), (0xfffffe9, 28),
    (0xfffffea, 28), (0x3ffffffd, 30), (0xfffffeb, 28), (0xfffffec, 28), (0xfffffed, 28), (0xfffffee, 28),
    (0xfffffef, 28), (0xffffff0, 28), (0xffffff1, 28), (0xffffff2, 28), (0x3ffffffe, 30), (0xffffff3, 28),
    (0xffffff4, 28), (0xffffff5, 28), (0xffffff6, 28), (0xffffff7, 28), (0xffffff8, 28), (0xffffff9, 28),
    (0xffffffa, 28), (0xffffffb, 28), (0x14, 6), (0x3f8, 10), (0x3f9, 10), (0xffa, 12), (0x1ff9, 13),
    (0x15, 6), (0xf8, 8), (0x7fa, 11), (0x3fa, 10), (0x3fb, 10), (0xf9, 8), (0x7fb, 11), (0xfa, 8),
    (0x16, 6), (0x17, 6), (0x18, 6), (0x0, 5), (0x1, 5), (0x2, 5), (0x19, 6), (0x1a, 6), (0x1b, 6),
    (0x1c, 6), (0x1d, 6), (0x1e, 6), (0x1f, 6), (0x5c, 7), (0xfb, 8), (0x7ffc, 15), (0x20, 6),
    (0xffb, 12), (0x3fc, 10), (0x1ffa, 13), (0x21, 6), (0x5d, 7), (0x5e, 7), (0x5f, 7), (0x60, 7),
    (0x61, 7), (0x62, 7), (0x63, 7), (0x64, 7), (0x65, 7), (0x66, 7), (0x67, 7), (0x68, 7), (0x69, 7),
    (0x6a, 7), (0x6b, 7), (0x6c, 7), (0x6d, 7), (0x6e, 7), (0x6f, 7), (0x70, 7), (0x71, 7), (0x72, 7),
    (0xfc, 8), (0x73, 7), (0xfd, 8), (0x1ffb, 13), (0x7fff0, 19), (0x1ffc, 13), (0x3ffc, 14), (0x22, 6),
    (0x7ffd, 15), (0x3, 5), (0x23, 6), (0x4, 5), (0x24, 6), (0x5, 5), (0x25, 6), (0x26, 6), (0x27, 6),
    (0x6, 5), (0x74, 7), (0x75, 7), (0x28, 6), (0x29, 6), (0x2a, 6), (0x7, 5), (0x2b, 6), (0x76, 7),
    (0x2c, 6), (0x8, 5), (0x9, 5), (0x2d, 6), (0x77, 7), (0x78, 7), (0x79, 7), (0x7a, 7), (0x7b, 7),
    (0x7ffe, 15), (0x7fc, 11), (0x3ffd, 14), (0x1ffd, 13), (0xffffffc, 28), (0xfffe6, 20), (0x3fffd2, 22),
    (0xfffe7, 20), (0xfffe8, 20), (0x3fffd3, 22), (0x3fffd4, 22), (0x3fffd5, 22), (0x7fffd9, 23),
    (0x3fffd6, 22), (0x7fffda, 23), (0x7fffdb, 23), (0x7fffdc, 23), (0x7fffdd, 23), (0x7fffde, 23),
    (0xffffeb, 24), (0x7fffdf, 23), (0xffffec, 24), (0xffffed, 24), (0x3fffd7, 22), (0x7fffe0, 23),
    (0xffffee, 24), (0x7fffe1, 23), (0x7fffe2, 23), (0x7fffe3, 23), (0x7fffe4, 23), (0x1fffdc, 21),
    (0x3fffd8, 22), (0x7fffe5, 23), (0x3fffd9, 22), (0x7fffe6, 23), (0x7fffe7, 23), (0xffffef, 24),
    (0x3fffda, 22), (0x1fffdd, 21), (0xfffe9, 20), (0x3fffdb, 22), (0x3fffdc, 22), (0x7fffe8, 23),
    (0x7fffe9, 23), (0x1fffde, 21), (0x7fffea, 23), (0x3fffdd, 22), (0x3fffde, 22), (0xfffff0, 24),
    (0x1fffdf, 21), (0x3fffdf, 22), (0x7fffeb, 23), (0x7fffec, 23), (0x1fffe0, 21), (0x1fffe1, 21),
    (0x3fffe0, 22), (0x1fffe2, 21), (0x7fffed, 23), (0x3fffe1, 22), (0x7fffee, 23), (0x7fffef, 23),
    (0xfffea, 20), (0x3fffe2, 22), (0x3fffe3, 22), (0x3fffe4, 22), (0x7ffff0, 23), (0x3fffe5, 22),
    (0x3fffe6, 22), (0x7ffff1, 23), (0x3ffffe0, 26), (0x3ffffe1, 26), (0xfffeb, 20), (0x7fff1, 19),
    (0x3fffe7, 22), (0x7ffff2, 23), (0x3fffe8, 22), (0x1ffffec, 25), (0x3ffffe2, 26), (0x3ffffe3, 26),
    (0x3ffffe4, 26), (0x7ffffde, 27), (0x7ffffdf, 27), (0x3ffffe5, 26), (0xfffff1, 24), (0x1ffffed, 25),
    (0x7fff2, 19), (0x1fffe3, 21), (0x3ffffe6, 26), (0x7ffffe0, 27), (0x7ffffe1, 27), (0x3ffffe7, 26),
    (0x7ffffe2, 27), (0xfffff2, 24), (0x1fffe4, 21), (0x1fffe5, 21), (0x3ffffe8, 26), (0x3ffffe9, 26),
    (0xffffffd, 28), (0x7ffffe3, 27), (0x7ffffe4, 27), (0x7ffffe5, 27), (0xfffec, 20), (0xfffff3, 24),
    (0xfffed, 20), (0x1fffe6, 21), (0x3fffe9, 22), (0x1fffe7, 21), (0x1fffe8, 21), (0x7ffff3, 23),
    (0x3fffea, 22), (0x3fffeb, 22), (0x1ffffee, 25), (0x1ffffef, 25), (0xfffff4, 24), (0xfffff5, 24),
    (0x3ffffea, 26), (0x7ffff4, 23), (0x3ffffeb, 26), (0x7ffffe6, 27), (0x3ffffec, 26), (0x3ffffed, 26),
    (0x7ffffe7, 27), (0x7ffffe8, 27), (0x7ffffe9, 27), (0x7ffffea, 27), (0x7ffffeb, 27), (0xffffffe, 28),
    (0x7ffffec, 27), (0x7ffffed, 27), (0x7ffffee, 27), (0x7ffffef, 27), (0x7fffff0, 27), (0x3ffffee, 26),
    (0x3fffffff, 30),
]


def huff_decode(data):
    """HPACK Huffman 解码（逐位匹配）"""
    table = {}
    for sym, (code, bits) in enumerate(HUFF):
        table[(code, bits)] = sym
    out = bytearray()
    cur = 0
    nbits = 0
    for byte in data:
        for i in range(7, -1, -1):
            cur = (cur << 1) | ((byte >> i) & 1)
            nbits += 1
            if nbits > 30:
                return None
            if (cur, nbits) in table:
                out.append(table[(cur, nbits)])
                cur = 0
                nbits = 0
    return bytes(out)


def hpack_str(buf, i):
    if i >= len(buf):
        return "", i
    huff = buf[i] & 0x80
    l, i = hpack_int(buf, i, 7)
    s = buf[i:i + l]
    i += l
    if huff:
        d = huff_decode(s)
        if d is not None:
            try:
                return d.decode("utf-8", "replace"), i
            except Exception:
                return d.decode("latin-1"), i
        return "<huffman-fail:%s>" % s.hex(), i
    try:
        return s.decode("latin-1"), i
    except Exception:
        return "<bin>", i


def hpack_decode(buf):
    """解出 header 列表（动态表逐帧维护）"""
    out = []
    dyn = []
    i = 0
    while i < len(buf):
        b = buf[i]
        try:
            if b & 0x80:                                    # 索引字段 (1xxxxxxx)
                idx, i = hpack_int(buf, i, 7)
                if 0 < idx < len(HPACK_STATIC):
                    out.append(HPACK_STATIC[idx])
                elif idx - len(HPACK_STATIC) - 1 < len(dyn):
                    out.append(dyn[idx - len(HPACK_STATIC) - 1])
                else:
                    out.append(("<idx %d>" % idx, ""))
            elif b & 0x40:                                  # 增量索引 (01xxxxxx)
                idx, i = hpack_int(buf, i, 6)
                name = HPACK_STATIC[idx][0] if 0 < idx < len(HPACK_STATIC) else None
                if name is None:
                    name, i = hpack_str(buf, i)
                val, i = hpack_str(buf, i)
                out.append((name, val))
                dyn.insert(0, (name, val))
            elif b & 0x20:                                  # 动态表大小更新
                _, i = hpack_int(buf, i, 5)
            else:                                           # 无索引 (0000xxxx)
                idx, i = hpack_int(buf, i, 4)
                name = HPACK_STATIC[idx][0] if 0 < idx < len(HPACK_STATIC) else None
                if name is None:
                    name, i = hpack_str(buf, i)
                val, i = hpack_str(buf, i)
                out.append((name, val))
        except Exception:
            break
    return out


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def find_comment_btn():
    """动态定位评论按钮坐标（评论少的视频坐标不同）"""
    import re as _re
    try:
        adb("shell", "rm", "-f", "/sdcard/ui.xml")
        adb("shell", "uiautomator", "dump", "/sdcard/ui.xml")
        xml = adb("shell", "cat", "/sdcard/ui.xml").stdout or ""
        for n in _re.findall(r"<node[^>]+>", xml):
            if "评论" in n and 'clickable="true"' in n:
                m = _re.search(r'bounds="\[(\d+),(\d+)\]\[(\d+),(\d+)\]"', n)
                if m:
                    x1, y1, x2, y2 = map(int, m.groups())
                    return ((x1 + x2) // 2, (y1 + y2) // 2)
    except Exception:
        pass
    return None


def frames_to_headers(frames):
    """解析所有帧 → header 组列表"""
    out = []
    for meta, data in frames:
        if len(data) < 10:
            continue
        off = 0
        if data[:2] == b"PR":
            off += 24
        while off + 9 <= len(data):
            ln = int.from_bytes(data[off:off + 3], "big")
            typ = data[off + 3]
            if off + 9 + ln > len(data):
                ln = len(data) - off - 9
            payload = data[off + 9:off + 9 + ln]
            if typ == 1 and payload:
                flags = data[off + 4]
                p = payload
                if flags & 0x08 and p:
                    pad = p[0]
                    p = p[1:len(p) - pad]
                if flags & 0x20:
                    p = p[5:]
                try:
                    hdrs = hpack_decode(p)
                    if hdrs:
                        out.append(hdrs)
                except Exception:
                    pass
            off += 9 + ln
    return out


def getk(h, k):
    for n, v in h:
        if n == k:
            return v
    return None


def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
    session = dev.attach(int(pid[0]))
    sc = session.create_script(open(JS, encoding="utf-8").read())

    frames = []

    def on_msg(m, data):
        if m.get("type") == "send" and data:
            frames.append((m.get("payload", {}), bytes(data)))

    sc.on("message", on_msg)
    sc.load()
    print("[*] hooking SSL_write...")
    time.sleep(2)

    # 1) 打开视频
    adb("shell", "am", "start", "-a", "android.intent.action.VIEW",
        "-d", f"snssdk1128://aweme/detail/{AID}")
    time.sleep(7)
    n0 = len(frames)

    # 2) 动态定位评论按钮并点击（触发 /comment/list/stream/）
    c = find_comment_btn()
    if c:
        print(f"[*] 点击评论按钮 @ {c}")
        adb("shell", "input", "tap", str(c[0]), str(c[1]))
    else:
        print("[!] 未找到评论按钮，尝试默认坐标")
        adb("shell", "input", "tap", "997", "1370")

    # 3) 采集窗口：点击后持续采集（多轮翻页，最大化命中机会）
    print("[*] 采集评论帧（点击后 25 秒，含 3 次翻页）...")
    for i in range(3):
        time.sleep(7)
        adb("shell", "input", "swipe", "540", "1900", "540", "900", "400")
        print(f"    swipe {i+1}, frames={len(frames)}")
    time.sleep(4)
    session.detach()

    print(f"[*] 共收到 {len(frames)} 帧（点击前 {n0}）")
    allh = frames_to_headers(frames)
    cmt = [h for h in allh if "/comment/list/" in (getk(h, ":path") or "")]

    # 若未命中评论帧，尝试从"任意帧"里找 signature 头（同一 App 的头是共享的）
    print(f"[*] header 组 {len(allh)}，评论请求 {len(cmt)} 组")

    def has_sig(h):
        for n, _ in h:
            if n and ("tt-token" in n.lower() or "ticket-guard" in n.lower()
                      or "x-tt-token-supplement" in n.lower()):
                return True
        return False

    sig_groups = [h for h in allh if has_sig(h)]
    print(f"[*] 含签名头的组（任意接口）: {len(sig_groups)}")

    if sig_groups:
        h = sig_groups[0]
        print("  === 完整签名头（来自 " + str(getk(h, ':path'))[:60] + "）===")
        for n, v in h:
            print(f"    {n}: {str(v)[:160]}")
        json.dump({"headers": [[n, v] for n, v in h],
                   "sourcePath": getk(h, ":path"),
                   "authority": getk(h, ":authority")},
                  open(os.path.join(OUTDIR, "signature_headers.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print("[*] 已保存 -> signature_headers.json")

    if not cmt:
        paths = sorted({(getk(h, ":path") or "?")[:60] for h in allh})
        print("[!] 未捕获评论帧（判定：评论接口走 QUIC，不经 SSL_write）")
        for p in paths[:25]:
            print("     ", p)
        return 1 if not sig_groups else 0

    h = cmt[0]
    print("  === 评论请求完整 header ===")
    for n, v in h:
        print(f"    {n}: {str(v)[:150]}")
    json.dump({"headers": [[n, v] for n, v in h],
               "path": getk(h, ":path"),
               "authority": getk(h, ":authority"),
               "method": getk(h, ":method")},
              open(os.path.join(OUTDIR, "comment_h2_headers.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[*] 已保存 -> comment_h2_headers.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
