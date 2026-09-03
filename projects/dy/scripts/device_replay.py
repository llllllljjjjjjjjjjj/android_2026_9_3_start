# -*- coding: utf-8 -*-
# device_replay.py — 真机参数 + oracle 八神 组合重放
# 输入: capture/device_main_search.json（hook38 抓的真机最新 general/stream 请求）
# body: 由模板（charles_session5 entry74 明文参数集）重建，keyword/count/cursor 可换
# 八神: oracle（dy_hook21.js RPC）现场生成
import argparse
import base64
import json
import socket
import subprocess
import time
import urllib.parse
import uuid
from pathlib import Path

import frida
import requests
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook21.js"
CAP = ROOT / "capture" / "device_main_search.json"
TPL_SESSION = ROOT / "capture" / "charles_session5.json"

_orig_gai = socket.getaddrinfo


def _gai_v4(host, *a, **k):
    return [x for x in _orig_gai(host, *a, **k) if x[0] == socket.AF_INET] or _orig_gai(host, *a, **k)


socket.getaddrinfo = _gai_v4

_script = None


def oracle_connect():
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    _script = dev.attach(pid).create_script(open(HOOK, encoding="utf-8").read())
    _script.load()
    time.sleep(2)


def oracle_sign(url, stub, headers_str):
    global _script
    if _script is None:
        oracle_connect()
    out = _script.exports_sync.oracle(url, headers_str + "\r\nx-ss-stub\r\n" + stub)
    parts = out.split("\r\n")
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


def build_body(keyword, count=10, cursor=0, session_id=None):
    """从 entry74 明文参数集重建 body（全量参数，仅换可变字段）。"""
    d = json.loads(TPL_SESSION.read_text(encoding="utf-8-sig"))
    e = d[74]
    raw = base64.b64decode(e["request"]["body"]["encoded"])
    plain = zstd.ZstdDecompressor().decompressobj().decompress(raw).decode("utf-8", "replace")
    form = {k: v[0] for k, v in urllib.parse.parse_qs(plain, keep_blank_values=True).items()}
    form["keyword"] = keyword
    form["count"] = str(count)
    form["cursor"] = str(cursor)
    form["filter_selected"] = json.dumps({"sort_type": "0", "publish_time": "0", "filter_duration": ""},
                                         ensure_ascii=False)
    form["search_session_id"] = session_id or str(uuid.uuid4())
    form["search_session_round"] = "1"
    try:
        bc = json.loads(form.get("bcm_chain", "{}"))
        for c in bc.get("chain", []):
            c["btm_show_id"] = str(uuid.uuid4()) + "#" + c.get("btm_show_id", "0").split("#")[-1]
        form["bcm_chain"] = json.dumps(bc, ensure_ascii=False)
    except Exception:
        pass
    return zstd.ZstdCompressor(level=3).compress(urllib.parse.urlencode(form).encode())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kw", default=None)
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--cursor", type=int, default=0)
    ap.add_argument("--plain", action="store_true", help="body 发明文表单（去 zstd 标记，响应可读）")
    args = ap.parse_args()

    cap = json.loads(CAP.read_text(encoding="utf-8"))
    url = cap["url"]
    hstr = cap["headers"]
    # headers 串 → dict
    hdrs = {}
    lines = hstr.split("\r\n")
    for i in range(0, len(lines) - 1, 2):
        name = lines[i].strip()
        if name:
            hdrs[name] = lines[i + 1]
    kw = args.kw or (cap.get("kw") or "麻辣烫")
    if args.plain:
        # 明文通道：body 不压缩，去掉 zstd 标记，服务器直接读表单且回普通 JSON
        d = json.loads(TPL_SESSION.read_text(encoding="utf-8-sig"))
        e = d[74]
        raw = base64.b64decode(e["request"]["body"]["encoded"])
        plain0 = zstd.ZstdDecompressor().decompressobj().decompress(raw).decode("utf-8", "replace")
        form = {k: v[0] for k, v in urllib.parse.parse_qs(plain0, keep_blank_values=True).items()}
        form["keyword"] = kw
        form["count"] = str(args.count)
        form["cursor"] = str(args.cursor)
        form["filter_selected"] = json.dumps({"sort_type": "0", "publish_time": "0", "filter_duration": ""},
                                             ensure_ascii=False)
        form["search_session_id"] = str(uuid.uuid4())
        form["search_session_round"] = "1"
        body = urllib.parse.urlencode(form).encode()
        hdrs.pop("x-bd-content-encoding", None)
        hdrs.pop("ttzip-version", None)
        hdrs.pop("content-length", None)
    else:
        body = build_body(kw, args.count, args.cursor)
    stub = hdrs.get("x-ss-stub", "0123456789abcdef0123456789abcdef")
    hdrs.pop("content-length", None)
    for k in list(hdrs):
        if k.lower() in ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa"):
            del hdrs[k]
    hdrs.update(oracle_sign(url, stub, hstr))
    hdrs["x-ss-req-ticket"] = str(int(time.time() * 1000))

    s = requests.Session()
    s.trust_env = False
    r = s.post(url, headers=hdrs, data=body, timeout=30)
    raw = r.content
    if raw[:4] == b"\x28\xb5\x2f\xfd":
        try:
            ddict = zstd.ZstdCompressionDict((ROOT / "capture" / "search_bodies" / "template_dict_v1.zstdict").read_bytes())
            raw = zstd.ZstdDecompressor(dict_data=ddict).decompressobj().decompress(raw)
        except Exception:
            print("[!] dict-zstd 响应解不开")
    si = raw.find(b"{")
    if si > 0:
        raw = raw[si:]
    j = json.JSONDecoder().raw_decode(raw.decode("utf-8", errors="replace"))[0]
    print("status_code =", j.get("status_code"))
    lp = j.get("log_pb") or {}
    nil = (lp.get("stab_extra") or {}).get("NilInfoContext") or {}
    print("nil:", nil.get("search_nil_type"), "/", nil.get("search_nil_item"))
    print("top keys:", list(j.keys())[:8])
    st = j.get("struct") or {}
    print("struct:", (list(st.keys())[:6] if isinstance(st, dict) else st))


if __name__ == "__main__":
    main()
