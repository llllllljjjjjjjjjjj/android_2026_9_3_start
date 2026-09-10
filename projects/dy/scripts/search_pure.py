# -*- coding: utf-8 -*-
"""dy 搜索接口 —— 纯算直发（离线，不依赖真机 / Frida RPC / App 运行态）

交付定位（按 AGENTS.md 三级交付门）:
  - 业务参数 + 公共参数: 解析型纯算（本地生成；来源见 docs/parameter-lineage.md）
  - 签名头（八神 x-argus/gorgon + ClientKey + TicketGuard + Cookie）:
    复用 native 层 HPACK 解码抓取的实样（capture/h2_headers.json / signature_headers.json，多份轮换）。
    跨接口复用有效性已实证（docs/protocol-direct.md：带签名头直发 -99999 消失）。
  - 风控配对: 按 docs/flow-and-risk.md 实证，主请求必须与紧邻特征上报配对（缺一即软降级 hit_shark）,
    本脚本默认三连发: history_words_record(前置) -> general/stream(主) -> upload_ei_feature(特征)
  - 若仍触发 antispam_check/hit_shark（归因结论见 docs/search-pure.md）:
    根因 = TLS 客户端指纹(JA3/JA4) 与 App Cronet 不符（设备/账号/IP/内容/协议均已实证排除），
    纯离线直发不可解，需真机转发或 TLS 指纹模拟（环境对抗）。

用法:
  python search_pure.py <keyword> [count] [cursor] [--sig N] [--no-pair] [--out FILE]

数据来源:
  - body 模板 : capture/body_full.txt (@@@REQ ... @@BODY_BEGIN..END: history_words_record / general/stream / upload_ei_feature)
  - 签名头   : capture/h2_headers.json（多份样本轮换） / capture/signature_headers.json
  - 公共参数 : 抓包 :path 中的 TTNet 公共参数实样（设备常量保持，ts/_rticket 本地生成）
"""
import json, os, sys, time, uuid, gzip, re, argparse
import urllib.parse
import requests

BASE = r"D:\reserve_agent\android\projects\dy"
CAP = os.path.join(BASE, "capture")
BODY_FILE = os.path.join(CAP, "body_full.txt")
REAL_BODY_FILE = os.path.join(CAP, "search_body_real.json")   # 真实捕获搜索 body（RequestBuilder, kw=太阳）
H2_FILE = os.path.join(CAP, "h2_headers.json")
SIG_FILE = os.path.join(CAP, "signature_headers.json")
FRESH_FILE = os.path.join(CAP, "signature_headers_fresh.json")   # 最新抓包样本（优先）

SEARCH_PATH = "/aweme/v2/search/general/stream/"
SEARCH_HOST = "search3-search.amemv.com"        # host 调度实证: 搜索 -> search3-search.amemv.com
HISTORY_PATH = "/aweme/v1/search/history_words_record/"
HISTORY_HOST = "i.snssdk.com"
FEATURE_PATH = "/aweme/v1/search/memory/upload_ei_feature/"
FEATURE_HOST = "aweme.snssdk.com"

# 长期令牌/设备常量（跨请求逐字不变，来自抓包实样；纯算本地保持）
LONG_LIVED_HEADERS = [
    "x-tt-dt", "x-bd-kmsv", "x-vc-bdturing-sdk-version", "sdk-version",
    "x-tt-passport-mfa-token", "x-tt-token", "x-tt-token-supplement",
    "bd-ticket-guard-key-sign", "passport-sdk-settings", "passport-sdk-version",
    "token-tlb-tag", "session-tlb-tag", "x-tt-store-region", "x-tt-store-region-src",
    "x-ss-dp", "bd-ticket-guard-display-os-version", "bd-ticket-guard-version",
    "bd-ticket-guard-iteration-version", "bd-ticket-guard-ree-public-key",
]
# 八神/风控族: 每次请求变化 -> 从样本轮换
ROTATING_HEADERS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa"]


def read_text(path):
    """自适应解码（PowerShell Tee-Object 可能写 UTF-16LE）"""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16", errors="ignore")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig", errors="ignore")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", errors="ignore")


def load_header_samples():
    """加载抓包签名头样本，返回 [ {headers, pseudo} ]"""
    samples = []
    for p in (FRESH_FILE, H2_FILE, SIG_FILE):
        if not os.path.exists(p):
            continue
        try:
            j = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            print(f"[!] 加载 {p} 失败: {e}")
            continue
        if isinstance(j, list):
            for it in j:
                if isinstance(it, list) and it and isinstance(it[0], list):
                    samples.append(_norm_sample(it))          # h2_headers.json: [[hdr,...],...]
                elif isinstance(it, dict) and "value" in it:
                    samples.append(_norm_sample(it["value"]))
        elif isinstance(j, dict) and "headers" in j:
            samples.append(_norm_sample(j["headers"]))
    return samples


def _norm_sample(header_list):
    hdrs = {}
    cookies = []
    pseudo = {}
    for n, v in header_list:
        n, v = str(n), str(v)
        if n.startswith(":"):
            pseudo[n] = v
        elif n.lower() == "cookie":
            cookies.append(v)
        else:
            hdrs[n] = v
    if cookies:
        hdrs["Cookie"] = "; ".join(cookies)
    return {"headers": hdrs, "pseudo": pseudo}


def pick_query_sample(samples):
    """选公共参数最全的样本作 URL query 模板（含 iid/device_id/aid/ts 的完整 TTNet 参数）"""
    best, best_n = None, -1
    for s in samples:
        path = s.get("pseudo", {}).get(":path") or ""
        if "?" not in path:
            continue
        params = dict(urllib.parse.parse_qsl(path.split("?", 1)[1]))
        n = sum(1 for k in ("iid", "device_id", "aid", "ts", "app_name") if k in params)
        if n > best_n:
            best, best_n = s, n
    return best or (samples[0] if samples else None)


def extract_bodies():
    """从 body_full.txt 提取三个接口的 body 模板: {path: body}（各取第一条）
    SEARCH_PATH 优先使用真实捕获模板（search_body_real.json，含完整行为特征参数）"""
    out = {}
    # 真实模板优先
    if os.path.exists(REAL_BODY_FILE):
        try:
            j = json.load(open(REAL_BODY_FILE, encoding="utf-8"))
            if j.get("body"):
                out[SEARCH_PATH] = j["body"]
        except Exception:
            pass
    lines = read_text(BODY_FILE).splitlines()
    paths = (HISTORY_PATH, SEARCH_PATH, FEATURE_PATH)
    for i, l in enumerate(lines):
        if "@@@REQ" not in l:
            continue
        hit = next((p for p in paths if p in l), None)
        if not hit or hit in out:
            continue
        for j in range(i, min(i + 12, len(lines))):
            if lines[j].strip() == "@@@BODY_BEGIN":
                buf = []
                k = j + 1
                while k < len(lines) and lines[k].strip() != "@@@BODY_END":
                    buf.append(lines[k])
                    k += 1
                out[hit] = "\n".join(buf)
                break
    return out


def build_public_query(sample, now_s, now_ms):
    """从抓包 :path 提取 TTNet 公共参数模板，动态替换时间戳；返回 query 字符串"""
    path = sample.get("pseudo", {}).get(":path") or ""
    qs = path.split("?", 1)[1] if "?" in path else ""
    if not qs:
        return ""
    params = dict(urllib.parse.parse_qsl(qs))
    params["ts"] = str(now_s)
    params["_rticket"] = str(now_ms)
    return "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())


def build_search_body(template, keyword, count, cursor, prev_search_ts_ms, search_id=None,
                      keep_features=False):
    """基于模板动态构造搜索 body（纯算：本地生成 + 模板保持）
    keep_features=True 时保留行为特征参数真实值（search_rerank_info/realtime_feature_channel/
    bcm_chain/pre_search_id_list/client_extra），仅替换核心动态字段——与真实 App 请求形态一致"""
    params = dict(urllib.parse.parse_qsl(template, keep_blank_values=True))
    params["keyword"] = keyword
    params["count"] = str(count)
    params["cursor"] = str(cursor)
    params["search_session_id"] = str(uuid.uuid4())
    params["previous_search_ts"] = str(prev_search_ts_ms)
    params["previous_search_query"] = keyword
    params["history_search_query_list"] = json.dumps([keyword], ensure_ascii=False)
    if search_id:
        params["search_id"] = search_id
        params["pre_search_id_list"] = json.dumps([search_id], ensure_ascii=False)
    elif not keep_features:
        params["pre_search_id_list"] = "[]"
    if not keep_features:
        # 旧模板: bcm_chain 保持模板 btm 结构，btm_show_id 换新 UUID（行为链本地生成）
        try:
            chain = json.loads(params.get("bcm_chain", "{}"))
            for item in chain.get("chain", []):
                sid = item.get("btm_show_id", "")
                if "#" in sid:
                    item["btm_show_id"] = f"{uuid.uuid4()}#{sid.split('#')[1]}"
            params["bcm_chain"] = json.dumps(chain, ensure_ascii=False)
        except Exception:
            pass  # 模板损坏则保持原样
    return "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())


def build_history_body(template, keyword, now_ms):
    """history_words_record body（JSON 模板，替换 word/timeStamp）"""
    try:
        j = json.loads(template)
    except Exception:
        return template
    for w in j.get("words", []):
        w["word"] = keyword
        w["timeStamp"] = now_ms
    return json.dumps(j, ensure_ascii=False)


def build_feature_body(template, session_id):
    """upload_ei_feature body（form 模板，替换 search_session_id）"""
    params = dict(urllib.parse.parse_qsl(template, keep_blank_values=True))
    params["search_session_id"] = session_id
    return "&".join(f"{k}={urllib.parse.quote(str(v), safe='')}" for k, v in params.items())


def build_headers(sample, now_s, now_ms, host, stub=None):
    """组装请求头: 长期令牌照抄 + 八神头轮换 + 时间戳头本地生成
    stub: x-ss-stub 由调用方离线计算（MD5(body) 大写 hex，已实证）"""
    hdrs = {}
    src = sample["headers"]
    for k in LONG_LIVED_HEADERS:
        if k in src:
            hdrs[k] = src[k]
    for k in ROTATING_HEADERS:
        if k in src:
            hdrs[k] = src[k]
    if "Cookie" in src:
        hdrs["Cookie"] = src["Cookie"]
    if "User-Agent" in src:
        hdrs["User-Agent"] = src["User-Agent"]
    if "x-tt-request-tag" in src:
        hdrs["x-tt-request-tag"] = src["x-tt-request-tag"]
    if "x-tt-trace-id" in src:
        hdrs["x-tt-trace-id"] = src["x-tt-trace-id"]
    if stub:
        hdrs["x-ss-stub"] = stub               # 纯算: MD5(body) 大写 hex
    hdrs["activity_now_client"] = str(now_ms)
    hdrs["x-ss-req-ticket"] = str(now_ms)
    hdrs.setdefault("User-Agent",
                    "com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; "
                    "Build/QQ3A.200605.001; Cronet/TTNetVersion:6f1e308d 2025-12-08)")
    hdrs["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    hdrs["Accept-Encoding"] = "gzip, deflate, br"
    hdrs["Host"] = host
    return hdrs


def compute_stub(body_bytes):
    """x-ss-stub 纯算: MD5(body) 大写 hex（字节级实证，见 docs/search-pure.md）"""
    import hashlib
    return hashlib.md5(body_bytes).hexdigest().upper()


def parse_response(raw):
    """解析响应: CRLF hex-len 分块流 / 直接 JSON / brotli-gzip；返回 (ok, verdict, texts, data)"""
    texts = []
    # 0) 整串直接 JSON
    try:
        j = json.loads(raw.decode("utf-8"))
        return _judge_json(j), [raw.decode("utf-8")], j
    except Exception:
        pass
    # 1) CRLF hex-len 分块（TTNet 流式明文 JSON 实测格式: "<hexlen>\r\n<json>\r\n...0\r\n"）
    parts = re.split(rb"\r\n", raw)
    for i in range(0, len(parts) - 1, 2):
        try:
            ln = int(parts[i], 16)
        except ValueError:
            continue
        payload = parts[i + 1]
        if len(payload) != ln or not payload:
            continue
        try:
            j = json.loads(payload.decode("utf-8"))
            texts.append(payload.decode("utf-8"))
        except Exception:
            continue
    if texts:
        # 合并判官：按信息量优先级 HAS_DATA > ANTISPAM > NIL_PAGE > EMPTY_SHELL
        order = {"HAS_DATA": 0, "ANTISPAM(hit_shark)": 1, "NIL_PAGE": 2, "EMPTY_SHELL": 3}
        best, best_ok, best_v = None, False, None
        for t in texts:
            j = json.loads(t)
            ok, verdict, _ = _judge_json(j)
            if verdict == "HAS_DATA":
                return True, "HAS_DATA", texts, j
            if best is None or order.get(verdict, 9) < order.get(best_v, 9):
                best, best_ok, best_v = j, ok, verdict
        return best_ok, best_v, texts, best
    # 2) brotli / gzip
    body = raw
    try:
        import brotli
        body = brotli.decompress(raw)
    except Exception:
        try:
            body = gzip.decompress(raw)
        except Exception:
            pass
    try:
        j = json.loads(body.decode("utf-8"))
        return _judge_json(j), [body.decode("utf-8")], j
    except Exception:
        pass
    return False, "UNPARSEABLE", [raw[:300].decode("utf-8", "ignore")], None


def _judge_json(j):
    """判官: -99999 风控拒绝 / hit_shark 反爬软降级 / 空壳 / 真实搜索结果"""
    if not isinstance(j, dict):
        return False, "NOT_OBJECT", j
    s = json.dumps(j)
    if "-99999" in s or j.get("status_code") == -99999:
        return False, "RISK_REJECTED(-99999)", j
    if "hit_shark" in s:
        return False, "ANTISPAM(hit_shark)", j
    if re.search(r'"aweme_id"|"aweme_list"|"aweme"', s):
        return True, "HAS_DATA", j
    if "search_nil_info" in s:
        return True, "NIL_PAGE", j
    return True, "EMPTY_SHELL", j


def extract_items(j):
    """从响应中提取搜索结果条目（兼容多种字段形态）"""
    if not isinstance(j, dict):
        return []
    items = []
    for key in ("aweme_list", "items"):
        v = j.get(key)
        if isinstance(v, list):
            for it in v:
                if isinstance(it, dict) and ("aweme_id" in it or "desc" in it):
                    items.append(it)
    if items:
        return items
    # 嵌套 data.aweme_list / category_list[].aweme_list
    d = j.get("data")
    if isinstance(d, dict):
        for key in ("aweme_list", "items"):
            v = d.get(key)
            if isinstance(v, list):
                for it in v:
                    if isinstance(it, dict) and ("aweme_id" in it or "desc" in it):
                        items.append(it)
    for cl in j.get("category_list") or []:
        if isinstance(cl, dict):
            items.extend(extract_items(cl))
    return items


def get_search_id(j):
    """从响应提取服务端下发的 search_id"""
    if not isinstance(j, dict):
        return None
    for key in ("search_id", "search_request_id"):
        v = j.get(key)
        if v:
            return v
    n = j.get("next_page")
    if isinstance(n, dict):
        v = n.get("search_id") or n.get("search_request_id")
        if v:
            return v
    return None


def main():
    ap = argparse.ArgumentParser(description="dy 搜索接口纯算直发（三连发风控配对）")
    ap.add_argument("keyword", help="搜索关键词（支持中文）")
    ap.add_argument("count", nargs="?", default="10", help="每页条数（默认 10）")
    ap.add_argument("cursor", nargs="?", default="0", help="游标（默认 0 第一页）")
    ap.add_argument("--sig", type=int, default=-1, help="签名样本序号（默认 0）")
    ap.add_argument("--no-pair", action="store_true", help="关闭前置/特征配对（仅主请求）")
    ap.add_argument("--out", default=None, help="输出 JSON 路径（默认 capture/pure_results_<kw>.json）")
    args = ap.parse_args()

    keyword = args.keyword
    count = int(args.count)
    cursor = int(args.cursor)

    samples = load_header_samples()
    if not samples:
        print("[!] 无签名头样本（需 capture/h2_headers.json 或 signature_headers.json）")
        return 1
    idx = args.sig if args.sig >= 0 else 0
    sample = samples[idx % len(samples)]
    query_sample = pick_query_sample(samples)   # 公共参数模板: 取参数最全的样本
    print(f"[*] 签名头样本 {len(samples)} 份 | 使用 #{idx % len(samples)}: {sample['pseudo'].get(':authority')}")
    print(f"[*] 公共参数模板来自: {query_sample['pseudo'].get(':authority')}")

    bodies = extract_bodies()
    tmpl_search = bodies.get(SEARCH_PATH)
    if not tmpl_search:
        print("[!] 无法从 body_full.txt 提取搜索 body 模板")
        return 1
    print(f"[*] body 模板: search={len(tmpl_search)}B "
          f"history={'Y' if HISTORY_PATH in bodies else 'N'} feature={'Y' if FEATURE_PATH in bodies else 'N'}")

    now_s = int(time.time())
    now_ms = int(time.time() * 1000)
    prev_ts = now_ms - 60000

    # 真实模板检测: 含完整行为特征参数 -> keep_features 模式（形态与真实 App 一致）
    tpl_params = dict(urllib.parse.parse_qsl(tmpl_search, keep_blank_values=True))
    keep_features = len(tpl_params.get("search_rerank_info", "")) > 100

    session_id = str(uuid.uuid4())
    search_id = None

    # ---- 1) 前置: history_words_record ----
    if not args.no_pair and HISTORY_PATH in bodies:
        url = f"https://{HISTORY_HOST}{HISTORY_PATH}?{build_public_query(query_sample, now_s, now_ms)}"
        hb = build_history_body(bodies[HISTORY_PATH], keyword, now_ms)
        hd = build_headers(sample, now_s, now_ms, HISTORY_HOST, compute_stub(hb.encode("utf-8")))
        try:
            r = requests.post(url, data=hb.encode("utf-8"), headers=hd, timeout=30)
            print(f"[*] 前置 history_words_record -> HTTP {r.status_code} ({len(r.content)}B)")
        except Exception as e:
            print(f"[!] 前置失败: {type(e).__name__} {e}")

    # ---- 2) 主请求: general/stream ----
    url = f"https://{SEARCH_HOST}{SEARCH_PATH}?{build_public_query(query_sample, now_s, now_ms)}"
    body = build_search_body(tmpl_search, keyword, count, cursor, prev_ts, search_id, keep_features)
    hdrs = build_headers(sample, now_s, now_ms, SEARCH_HOST, compute_stub(body.encode("utf-8")))
    print(f"[*] POST {SEARCH_HOST}{SEARCH_PATH}")
    print(f"[*] query {url.split('?')[1].count('&') + 1} 个 | body {len(body)}B | headers {len(hdrs)} 项")

    try:
        r = requests.post(url, data=body.encode("utf-8"), headers=hdrs, timeout=30)
    except Exception as e:
        print(f"[!] 请求失败: {type(e).__name__} {e}")
        return 2
    print(f"[*] HTTP {r.status_code} | CE: {r.headers.get('Content-Encoding')} | len={len(r.content)}")

    ok, verdict, texts, data = parse_response(r.content)
    print(f"[*] 判官: {verdict}")

    if data:
        sid = get_search_id(data)
        if sid:
            search_id = sid
            print(f"[*] 服务端签发 search_id: {sid}")

    items = extract_items(data) if data else []
    if items:
        print(f"[*] ★ 真实搜索结果 {len(items)} 条:")
        for it in items[:5]:
            print(f"    aid={it.get('aweme_id')} desc={str(it.get('desc'))[:50]}")
    else:
        for t in texts[:2]:
            print(f"[*] 响应块: {t[:300]}")

    # ---- 3) 特征上报: upload_ei_feature ----
    if not args.no_pair and FEATURE_PATH in bodies:
        url3 = f"https://{FEATURE_HOST}{FEATURE_PATH}?{build_public_query(query_sample, now_s, now_ms)}"
        fb = build_feature_body(bodies[FEATURE_PATH], session_id)
        hd3 = build_headers(sample, now_s, now_ms, FEATURE_HOST, compute_stub(fb.encode("utf-8")))
        try:
            r3 = requests.post(url3, data=fb.encode("utf-8"), headers=hd3, timeout=30)
            print(f"[*] 特征 upload_ei_feature -> HTTP {r3.status_code} ({len(r3.content)}B)")
        except Exception as e:
            print(f"[!] 特征上报失败: {type(e).__name__} {e}")

    out = args.out or os.path.join(CAP, f"pure_results_{keyword}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"keyword": keyword, "verdict": verdict, "ok": ok, "search_id": search_id,
                   "session_id": session_id, "items": items,
                   "raw_blocks": texts[:5] if not items else []},
                  f, ensure_ascii=False, indent=1)
    print(f"[*] 已保存 -> {out}")
    return 0 if (ok and items) else (3 if not ok else 4)


if __name__ == "__main__":
    sys.exit(main())
