# -*- coding: utf-8 -*-
# dy_search.py — 抖音搜索接口复刻客户端（最终版，2026-08-28）
#
# 依据 Charles 抓包（capture/charles_session4.json entry[63]/[301]）实证：
#   接口: POST https://search5-search-m-hj.amemv.com/aweme/v2/search/general/stream/
#         （single 为同参数单请求版；sug 为 GET /aweme/v1/search/sug/）
#   body: zstd 压缩的 x-www-form-urlencoded（头 x-bd-content-encoding=zstd, ttzip-version=search_api）
#   body 关键参数: keyword / count / cursor(=offset) /
#         filter_selected={"sort_type":"0","publish_time":"0","filter_duration":""} /
#         query_correct_type / search_scene=douyin_search / search_session_id / token=search
#   签名: 八神头(X-Argus/X-Gorgon/X-Helios/X-Khronos/X-Ladon/X-Medusa) + x-ss-stub
#         由 hooks/dy_hook21.js RPC oracle 现场生成
#
# 用法:
#   python dy_search.py --kw 美食 --count 10 --cursor 0
#   python dy_search.py --kw meishi --pages 3          # 翻页（cursor=上页返回 cursor）
#   python dy_search.py --kw 美食 --endpoint single    # 用 general/single
import argparse
import base64
import json
import socket
import subprocess
import sys
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

# 强制 IPv4（PC DNS 解析 amemv 到 IPv6 会挂起）
_orig_gai = socket.getaddrinfo


def _gai_v4(host, *a, **k):
    return [x for x in _orig_gai(host, *a, **k) if x[0] == socket.AF_INET] or _orig_gai(host, *a, **k)


socket.getaddrinfo = _gai_v4

# ---- cookie：优先读 capture/fresh_cookie.txt（Charles 抓到的最新会话），无则用内置 ----
_COOKIE_FILE = ROOT / "capture" / "fresh_cookie.txt"


def _load_cookie():
    if _COOKIE_FILE.exists():
        c = _COOKIE_FILE.read_text(encoding="utf-8").strip()
        if c:
            return c
    return ("passport_csrf_token=12c601e8e7df1ed89ba5ad978753009a; "
            "passport_csrf_token_default=12c601e8e7df1ed89ba5ad978753009a; "
            "store-region=cn-jx; install_id=305014557150939; "
            "ttreq=1$acc983328eca331511c6dc5dd3f013547253a032; "
            "passport_mfa_token=CjbvWC3NoSIMkqXsr1%2FE5j%2F8KkbOF6VHVM5QPIVvNBEfSBGhae3sN4PSLDXKE%2Fl7unz%2FD52Cn64aSgo8AAAAAAAAAAAAAFDVmoacb9lMPUk3WmREPPX8m8QmS8q9rI5HjxsMPkx9yY2rpk4sOWk4DhcJ%2B2Kz3rU5F5j1XUpf8Q1lDsY%3D; "
            "d_ticket=4c6d14272b9fca48e3dac56463b81520ad96c; "
            "multi_sids=4280841314774051%3Aebbb8b854b25199d51e875b17642d4c1; "
            "sid_guard=ebbb8b854b25199d51e875b17642d4c1%7C1787888200%7C5184000%7CTue%2C+27-Oct-2026+03%3A36%3A40+GMT; "
            "uid_tt=10692bf0bde3060daf6c07e7004337d2; uid_tt_ss=10692bf0bde3060daf6c07e7004337d2; "
            "sid_tt=ebbb8b854b25199d51e875b17642d4c1; sessionid=ebbb8b854b25199d51e875b17642d4c1; "
            "sessionid_ss=ebbb8b854b25199d51e875b17642d4c1; "
            "session_tlb_tag=sttt%7C2%7C67uLhUslGZ1R6HWxdkLUwf________-5KlJHtWL9xD89PmQ8eJ0r-g5o4BrBToCo6rruEJBJHJk%3D; "
            "odin_tt=4a7dea5528ff8c3b8cb5a8b79962126f28bb59506f9c5c56d31465ee31f970da326935de732d82fac39dd942af12c006c421271b156a18c075669c79e14599c808737653280b8e; "
            "store-region-src=uid")


COOKIE = _load_cookie()

UA = ("com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; "
      "Build/QQ3A.200605.001; Cronet/TTNetVersion:6f1e308d 2025-12-08 QuicVersion:21ac1950 2025-11-18)")

# oracle 签名基础头（与 app 调 28065c 的 headers 输入同构）
BASE_HDR = ("cookie\r\n" + COOKIE + "\r\nuser-agent\r\n" + UA + "\r\naccept-encoding\r\ngzip, deflate, br")

DEVICE_PARAMS = {
    "klink_egdi": "AALY2YxB_O3DduzjVDys-ykyRSSELTpkokQCxdyLrut6q797RSP1A7Ti",
    "iid": "305014557150939", "device_id": "2310516478094584", "ac": "wifi",
    "channel": "huawei_1128_64", "aid": "1128", "app_name": "aweme",
    "version_code": "380000", "version_name": "38.0.0", "device_platform": "android",
    "os": "android", "ssmix": "a", "device_type": "Pixel 4", "device_brand": "google",
    "language": "zh", "os_api": "29", "os_version": "10", "manifest_version_code": "380001",
    "resolution": "1080*2236", "dpi": "440", "update_version_code": "38009900",
    "package": "com.ss.android.ugc.aweme", "first_launch_timestamp": "1787553883",
    "last_deeplink_update_version_code": "38009900", "cpu_support64": "true",
    "host_abi": "arm64-v8a", "is_guest_mode": "0", "app_type": "normal",
    "minor_status": "0", "appTheme": "light", "is_preinstall": "0",
    "need_personal_recommend": "1", "is_android_pad": "0", "is_android_fold": "0",
    "cdid": "6931eae8-ddbf-4063-9676-072161371940",
}

_script = None


def oracle_connect():
    global _script
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    _script = dev.attach(pid).create_script(open(HOOK, encoding="utf-8").read())
    _script.load()
    time.sleep(2)


def oracle_sign(url, stub):
    global _script
    if _script is None:
        oracle_connect()
    out = _script.exports_sync.oracle(url, BASE_HDR + "\r\nx-ss-stub\r\n" + stub)
    parts = out.split("\r\n")
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


# ---- 模板：Charles 抓到的真实搜索请求（charles_session5.json entry74，新身份）----
TEMPLATE_SESSION = ROOT / "capture" / "charles_session5.json"
TEMPLATE_ENTRY = 74
_template = None


def load_template():
    """加载真实请求模板：url / headers(不含八神) / body 明文。"""
    global _template
    if _template is not None:
        return _template
    if not TEMPLATE_SESSION.exists():
        return None
    d = json.loads(TEMPLATE_SESSION.read_text(encoding="utf-8-sig"))
    e = d[TEMPLATE_ENTRY]
    req = e.get("request") or {}
    url = f"https://{e['host']}{e['path']}?{e.get('query') or ''}"
    hdrs = {}
    for h in req.get("header", {}).get("headers", []):
        n = h.get("name", "")
        v = h.get("value", "")
        if n.startswith(":") or n.lower() in ("content-length",):
            continue
        if n.lower() in ("x-argus", "x-gorgon", "x-helios", "x-khronos", "x-ladon", "x-medusa"):
            continue
        hdrs[n] = v
    raw = base64.b64decode(req["body"]["encoded"])
    plain = zstd.ZstdDecompressor().decompressobj().decompress(raw).decode("utf-8", "replace")
    _template = {"url": url, "headers": hdrs, "plain": plain}
    return _template


def build_url(endpoint="stream"):
    t = load_template()
    if t:
        # 刷新 _rticket / ts，其余原样
        now = int(time.time())
        url = t["url"]
        import re as _re
        url = _re.sub(r"_rticket=\d+", "_rticket=" + str(now * 1000), url)
        url = _re.sub(r"(?<=[?&])ts=\d+", "ts=" + str(now), url)
        return url
    p = dict(DEVICE_PARAMS)
    now = int(time.time())
    p["_rticket"] = str(now * 1000 + int(uuid.uuid4().hex[:3], 16))
    p["ts"] = str(now)
    qs = urllib.parse.urlencode(p)
    return f"https://search5-search-m-hj.amemv.com/aweme/v2/search/general/{endpoint}/?{qs}"


def build_body(keyword, count=10, cursor=0, sort_type="0", publish_time="0",
               query_correct_type="1", search_session_id="", search_session_round="1"):
    """模板化 body：基于抓包明文替换可变参数（防重复请求检测），zstd 压缩。"""
    t = load_template()
    if t:
        form = urllib.parse.parse_qs(t["plain"], keep_blank_values=True)
        form = {k: v[0] for k, v in form.items()}
        form["keyword"] = keyword
        form["count"] = str(count)
        form["cursor"] = str(cursor)
        form["filter_selected"] = json.dumps({"sort_type": sort_type, "publish_time": publish_time,
                                              "filter_duration": ""}, ensure_ascii=False)
        form["query_correct_type"] = str(query_correct_type)
        form["search_session_id"] = search_session_id or str(uuid.uuid4())
        form["search_session_round"] = str(search_session_round)
        # bcm_chain btm_show_id 换新（防重放）
        try:
            bc = json.loads(form.get("bcm_chain", "{}"))
            for c in bc.get("chain", []):
                c["btm_show_id"] = str(uuid.uuid4()) + "#" + c.get("btm_show_id", "0").split("#")[-1]
            form["bcm_chain"] = json.dumps(bc, ensure_ascii=False)
        except Exception:
            pass
        plain = urllib.parse.urlencode(form).encode()
        return zstd.ZstdCompressor(level=3).compress(plain)
    form = {
        "keyword": keyword,
        "count": str(count),
        "cursor": str(cursor),
        "filter_selected": json.dumps({"sort_type": sort_type, "publish_time": publish_time,
                                       "filter_duration": ""}, ensure_ascii=False),
        "query_correct_type": query_correct_type,
        "search_source": "",
        "search_scene": "douyin_search",
        "nice_search_type": "general",
        "token": "search",
        "search_session_id": search_session_id or str(uuid.uuid4()),
        "search_session_round": str(search_session_round),
        "is_filter_search": "0",
        "need_filter_settings": "1",
        "from_group_id": "",
        "enter_from": "homepage_hot",
    }
    plain = urllib.parse.urlencode(form).encode()
    return zstd.ZstdCompressor(level=3).compress(plain)


def search(keyword, count=10, cursor=0, endpoint="stream", sort_type="0", publish_time="0",
           search_session_id="", stub=None, search_session_round="1"):
    t = load_template()
    url = build_url(endpoint)
    body = build_body(keyword, count, cursor, sort_type, publish_time, search_session_id=search_session_id,
                      search_session_round=search_session_round)
    stub = stub or ("0123456789abcdef0123456789abcdef" if stub is None else stub)
    if t:
        hdrs = dict(t["headers"])
        hdrs.pop("x-ss-stub", None)
        hdrs.pop("x-ss-req-ticket", None)
        hdrs["accept-encoding"] = "gzip, deflate"
        hdrs["x-ss-stub"] = stub
    else:
        hdrs = {
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "x-bd-content-encoding": "zstd",
            "ttzip-version": "search_api",
            "cookie": COOKIE,
            "user-agent": UA,
            "x-ss-stub": stub,
            "accept-encoding": "gzip, deflate, br",
        }
    hdrs.update(oracle_sign(url, stub))
    hdrs["x-ss-req-ticket"] = str(int(time.time() * 1000))
    # trust_env=False：绕过 Windows 系统代理（Charles 装好后 ProxyEnable=1 → 127.0.0.1:8888，
    # 会把 PC 直连也送进 Charles 导致自签证书校验失败），强制 PC 直连服务器
    s = requests.Session()
    s.trust_env = False
    r = s.post(url, headers=hdrs, data=body, timeout=30)
    raw = r.content
    if raw[:4] == b"\x28\xb5\x2f\xfd":
        # 字典 zstd 响应：优先用 APK 提取的字典，失败则放弃
        try:
            ddict = zstd.ZstdCompressionDict((ROOT / "capture" / "search_bodies" / "template_dict_v1.zstdict").read_bytes())
            raw = zstd.ZstdDecompressor(dict_data=ddict).decompressobj().decompress(raw)
        except Exception:
            return {"status_code": -1, "status_msg": "dict-zstd response undecodable"}
    s = raw.find(b"{")
    if s > 0:
        raw = raw[s:]
    return json.JSONDecoder().raw_decode(raw.decode("utf-8", errors="replace"))[0]


def parse_results(j):
    """提取搜索结果条目（aweme 视频 / user / challenge 等）。"""
    out = []
    for key in ("data", "data2", "search_data"):
        pass
    # general 返回结构：business_data / struct / render_info
    def walk(o, depth=0):
        if depth > 7:
            return
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("aweme_info", "aweme_list") and isinstance(v, list):
                    out.extend(v)
                elif k == "aweme" and isinstance(v, dict):
                    out.append(v)
                else:
                    walk(v, depth + 1)
        elif isinstance(o, list):
            for x in o:
                walk(x, depth + 1)
    walk(j)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kw", default="美食")
    ap.add_argument("--count", type=int, default=10)
    ap.add_argument("--cursor", type=int, default=0)
    ap.add_argument("--pages", type=int, default=1)
    ap.add_argument("--endpoint", choices=["stream", "single"], default="stream")
    ap.add_argument("--sort-type", default="0")
    ap.add_argument("--publish-time", default="0")
    ap.add_argument("--stub", default=None)
    args = ap.parse_args()

    cur = args.cursor
    sid = ""
    for pg in range(args.pages):
        print(f"\n=== page {pg + 1} cursor={cur} ===", flush=True)
        try:
            j = search(args.kw, args.count, cur, args.endpoint, args.sort_type,
                       args.publish_time, search_session_id=sid, stub=args.stub)
        except Exception as e:
            print("EXC:", e, flush=True)
            return
        print("status_code =", j.get("status_code"), flush=True)
        lp = j.get("log_pb") or {}
        nil = (lp.get("stab_extra") or {}).get("NilInfoContext") or {}
        if nil:
            print("nil:", nil.get("search_nil_type"), "/", nil.get("search_nil_item"), flush=True)
        aw = parse_results(j)
        print("aweme entries:", len(aw), flush=True)
        for a in aw[:5]:
            ai = a.get("aweme_info") or a
            if isinstance(a, dict) and "aweme" in a:
                ai = a["aweme"]
            if not isinstance(ai, dict):
                continue
            print("   -", (ai.get("desc") or "")[:50], "|", (ai.get("author") or {}).get("nickname", ""),
                  "|", ai.get("aweme_id"), flush=True)
        # 翻页 cursor
        nxt = lp.get("cursor") or (j.get("cursor"))
        if nxt is None or str(nxt) == str(cur):
            print("no next cursor, stop", flush=True)
            break
        cur = int(nxt)
        # 每页间隔，避免频控
        time.sleep(3)


if __name__ == "__main__":
    main()
