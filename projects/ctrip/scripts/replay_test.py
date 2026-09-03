"""
携程 SOA2 请求重放 + 频控/埋点实测脚本
用法：
  python replay_test.py --mode verify            # 基础重放验证（getServerIP）
  python replay_test.py --mode rate --interval 1.0 --pages 5   # 频控对拍
  python replay_test.py --mode ubt --variant full|drop|tamper   # 埋点强校验
"""
import os, sys, time, uuid, json, hashlib, argparse
import frida, requests

PKG = "ctrip.android.view"
SIGN_RPC = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\sign_rpc.js"
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

# 从抓包日志提取的 head 字段（设备/账号持久值）
HEAD = {
    "appid": "99999999",
    "auth": "B40F1A89800BEA2F3A03BF93929B3E695DE8EC9EAD6EE04D6266F772B3AA0224",
    "cid": "32001040290591014872",
    "ctok": "",
    "cver": "885.004",
    "lang": "01",
    "sauth": "",
    "sid": "8015",
    "syscode": "32",
}
DEVICE = {
    "DUID": "u=2206BC968FEBBDFECB7F8CD3C55EF8CF&v=0",
    "udl": "708D70C2B179E2F91CC5ED1C2CCE362D",
    "GUID": "32001040290591014872",
    "cticket": "B40F1A89800BEA2F3A03BF93929B3E695DE8EC9EAD6EE04D6266F772B3AA0224",
    "ubt_vid": "77019A70A2FF11F1F7264B115A5541FC",
}
UA = ("Dalvik/2.1.0 (Linux; U; Android 10; Pixel 4 Build/QQ3A.200605.001)_CtripAPP_Android_8.85.4_eb64_"
      "Ctrip_CtripWireless_8.85.4_cDevice=Pixel\\u204_cSize=w1080*h2236__v=885.004_os=Android_osv=10_"
      "m=Pixel\\u204_brand=google_vg=0_safeAreaTop=30_safeAreaB=0_SOAHTTP")

GW = "?__gw_appid=99999999&__gw_ver=885.004&__gw_os=Android&__gw_platform=APP"


def start_oracle():
    os.system(f'"{ADB}" start-server >nul 2>&1')
    os.system(f'"{ADB}" forward tcp:27042 tcp:27042 >nul 2>&1')
    time.sleep(1)
    device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = device.spawn([PKG])
    session = device.attach(pid)
    script = session.create_script(open(SIGN_RPC, encoding="utf-8").read())
    script.on("message", lambda m, d: None)
    script.load()
    device.resume(pid)
    time.sleep(4)  # 等冷启动完成
    return device, session, script


def build_headers(body_str, ubt_mode="full"):
    tid = uuid.uuid4().hex
    h = {
        "User-Agent": UA,
        "x-trip-syscode": "32",
        "x-trip-clientAppId": "99999999",
        "x-ctx-clientVersion": "885.004",
        "x-ctx-transactionId": str(uuid.uuid4()),
        "x-ctx-Currency": "CNY",
        "x-ctx-Locale": "zh-CN",
        "x-ctx-Region": "CN",
        "x-ctx-Unit": "METRIC",
        "x-ctx-Group": "ctrip",
        "cid": DEVICE["GUID"],
        "DUID": DEVICE["DUID"],
        "udl": DEVICE["udl"],
        "trip-trace-id": tid,
        "x-ctx-replaytraceid": tid,
        "Content-Type": "application/json;charset=utf-8",
    }
    # 埋点字段（x-ctx-ubt-*）
    if ubt_mode in ("full", "tamper"):
        h["x-ctx-ubt-vid"] = DEVICE["ubt_vid"] if ubt_mode == "full" else "FFFFFFFFFF" + DEVICE["ubt_vid"][10:]
        h["x-ctx-ubt-pageid"] = "hotel_inland_comment_detail"
        h["x-ctx-ubt-pvid"] = "1"
        h["x-ctx-ubt-sid"] = "1"
    # ubt_mode == "drop" 时不加任何 x-ctx-ubt-*
    return h


def make_body(url_path, biz_params):
    body = {"head": HEAD}
    body.update(biz_params)
    body_str = json.dumps(body, ensure_ascii=False, separators=(",", ":"))
    url = "https://m.ctrip.com" + url_path + GW
    return url, body_str


def post(url, body_str, sign=None, ubt_mode="full"):
    if sign is None:
        md5 = hashlib.md5(body_str.encode("utf-8")).hexdigest().lower()
        sign = script.exports_sync.sign(md5)
    headers = build_headers(body_str, ubt_mode)
    headers["x-payload-source"] = sign
    try:
        r = requests.post(url, data=body_str.encode("utf-8"), headers=headers, timeout=15)
        return r.status_code, r.text
    except Exception as e:
        return "ERR", str(e)


def verify():
    biz = {"appID": "99999999", "isOversea": False, "usingV4": True, "usingV4AliYun": False}
    url, body = make_body("/restapi/soa2/23196/json/getServerIP", biz)
    st, txt = post(url, body)
    print("[verify] getServerIP:", st, txt[:200])


def rate(interval, pages):
    path = "/restapi/soa2/23196/json/getServerIP"
    print(f"[rate] interval={interval}s pages={pages}")
    # 预生成 N 个不同 body（加随机 traceId），批量签名一次，避免连续 RPC 触发反检测
    urls, bodies, md5s = [], [], []
    for i in range(pages):
        biz = {"appID": "99999999", "isOversea": False, "usingV4": True, "usingV4AliYun": False,
               "traceId": uuid.uuid4().hex}
        url, body = make_body(path, biz)
        urls.append(url); bodies.append(body)
        md5s.append(hashlib.md5(body.encode("utf-8")).hexdigest().lower())
    signs = script.exports_sync.batch_sign(md5s)
    print(f"  [*] 批量签名 {len(signs)} 个完成")
    for i in range(pages):
        st, txt = post(urls[i], bodies[i], sign=signs[i])
        print(f"  #{i} status={st} resp={txt[:60]}")
        if st != 200:
            print("  !! 异常，可能触发频控")
            break
        time.sleep(interval)


def comment():
    # 构造点评列表请求（getCommentListRequest 扁平结构）
    path = "/restapi/soa2/24077/h5-json/clientHotelCommentList"
    def flat(scene_types):
        return {
            "pageIndex": 1,
            "sceneTypes": scene_types,
            "abtResults": [],
            "hotelId": 10650083138,
            "commentIdList": [],
            "roomSelectedFilter": [],
            "traverlSelectedFilter": [],
            "languageSelectedFilter": [],
            "sortSelectedFilter": [],
            "keyword": "",
            "selectedImageOnlyTag": False,
            "selectedNegativeTag": False,
            "repeatComment": 1,
            "mainTabSelectedId": 1,
            "subTabSelectedId": -400,
            "rooms": [],
            "travelTypes": [],
            "filterDateTypeList": [],
            "orderTypes": [],
        }
    # 完整扁平字段（含 null 可选字段）+ hotelId 类型变体
    def full(hotel_id, scene_types):
        return {
            "pageIndex": 1, "sceneTypes": scene_types, "abtResults": [],
            "hotelId": hotel_id, "extensionInfo": None, "commentIdList": [],
            "hotelSemantic": None, "searchNodeInfo": None,
            "roomSelectedFilter": [], "traverlSelectedFilter": [],
            "languageSelectedFilter": [], "sortSelectedFilter": [], "keyword": "",
            "selectedImageOnlyTag": False, "selectedNegativeTag": False,
            "selectedTagId": None, "repeatComment": 1,
            "mainTabSelectedId": 1, "subTabSelectedId": -400,
            "rooms": [], "travelTypes": [], "filterDateTypeList": [], "orderTypes": [],
            "sceneAiSummaryFilterCommonId": None, "sceneAiSummaryFilterAiItemId": None,
            "negativeSummaryIssueTagId": None,
        }
    # 用 batchSign 测 int 范围内 hotelId 的完整响应 + 翻页频控
    HID = 438006
    # 1) 单页完整响应
    url, body = make_body(path, full(HID, [1]))
    md5 = hashlib.md5(body.encode("utf-8")).hexdigest().lower()
    sign = script.exports_sync.sign(md5)
    st, txt = post(url, body, sign=sign)
    import re as _re2
    nm = _re2.search(r'"hotelName":"([^"]+)"|"hotelName":([^,}]+)', txt)
    city = _re2.search(r'"cityName":"([^"]+)"', txt)
    print(f"[comment] hotelId={HID} page1: status={st}")
    # 保存完整响应到文件，供分析酒店名称/评论结构
    open(r"D:\reserve_agent\ish-portable-kit\projects\ctrip\capture\comment_431041.json", "w", encoding="utf-8").write(txt)
    print(f"   resp len={len(txt)}")
    # 2) 翻页频控：pageIndex 2..N，批量签名
    pages = 6
    urls, bodies, md5s = [], [], []
    for pi in range(2, 2 + pages):
        b = full(HID, [1]); b["pageIndex"] = pi
        u, body = make_body(path, b)
        urls.append(u); bodies.append(body)
        md5s.append(hashlib.md5(body.encode("utf-8")).hexdigest().lower())
    signs = script.exports_sync.batch_sign(md5s)
    import time as _t
    for i, pi in enumerate(range(2, 2 + pages)):
        st, txt = post(urls[i], bodies[i], sign=signs[i])
        # 提取点评条数线索
        import re as _re
        cnt = _re.search(r'"commentCount":(\d+)|"totalCount":(\d+)', txt)
        err = _re.search(r'"Message":"([^"]+)"', txt)
        flag = ""
        if err: flag = " | ERR:" + err.group(1)
        elif cnt: flag = f" | count={cnt.group(1) or cnt.group(2)}"
        print(f"  page{pi}: status={st}{flag}")
        _t.sleep(0.5)


def ubt(variant):
    biz = {"appID": "99999999", "isOversea": False, "usingV4": True, "usingV4AliYun": False}
    url, body = make_body("/restapi/soa2/23196/json/getServerIP", biz)
    st, txt = post(url, body, ubt_mode=variant)
    print(f"[ubt] variant={variant}: status={st} resp={txt[:160]}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="verify")
    ap.add_argument("--interval", type=float, default=1.0)
    ap.add_argument("--pages", type=int, default=5)
    ap.add_argument("--variant", default="full")
    args = ap.parse_args()

    device, session, script = start_oracle()
    if args.mode == "verify":
        verify()
    elif args.mode == "rate":
        rate(args.interval, args.pages)
    elif args.mode == "ubt":
        ubt(args.variant)
    elif args.mode == "comment":
        comment()
