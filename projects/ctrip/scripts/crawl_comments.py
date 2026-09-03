"""
携程评论爬取脚本 —— 按风控对抗方案（拟人化节奏 + batchSign 规避反检测 + 完整请求头 + 止损）
目标：昆明海丽宾雅万达嘉华温泉酒店 (hotelId=438006)
输出：D:\111111\<run_id>\page_<页码>.json（每次运行新目录，不覆盖）
持续：20 分钟
"""
import os, sys, time, json, uuid, hashlib, random, re
import frida, requests

PKG = "ctrip.android.view"
SIGN_RPC = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\sign_rpc.js"
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

HOTEL_ID = 438006
PAGE_SIZE = 10
DURATION_MINUTES = 20
OUTPUT_ROOT = r"D:\111111"

# 风控方案：拟人化节奏参数（实测 0.5s 无频控，但按风控方案保守 1.5~3s）
INTERVAL_MIN = 1.5
INTERVAL_MAX = 3.0
BATCH_SIGN_SIZE = 6  # 每批预签名的页数（batchSign 一次拿多个，避免连续 RPC 触发反检测）

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
    "ubt_vid": "77019A70A2FF11F1F7264B115A5541FC",
}
UA = ("Dalvik/2.1.0 (Linux; U; Android 10; Pixel 4 Build/QQ3A.200605.001)_CtripAPP_Android_8.85.4_eb64_"
      "Ctrip_CtripWireless_8.85.4_cDevice=Pixel\\u204_cSize=w1080*h2236__v=885.004_os=Android_osv=10_"
      "m=Pixel\\u204_brand=google_vg=0_safeAreaTop=30_safeAreaB=0_SOAHTTP")
GW = "?__gw_appid=99999999&__gw_ver=885.004&__gw_os=Android&__gw_platform=APP"

script = None  # 全局 oracle script


def start_oracle():
    global script
    os.system(f'"{ADB}" start-server >nul 2>&1')
    os.system(f'"{ADB}" forward tcp:27042 tcp:27042 >nul 2>&1')
    time.sleep(1)
    device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = device.spawn([PKG])
    session = device.attach(pid)
    sc = session.create_script(open(SIGN_RPC, encoding="utf-8").read())
    sc.load()
    device.resume(pid)
    time.sleep(5)  # 等冷启动完成（避开反检测窗口）
    script = sc
    return device, session


def build_body(page_index):
    biz = {
        "pageIndex": page_index,
        "sceneTypes": [1],
        "abtResults": [],
        "hotelId": HOTEL_ID,
        "extensionInfo": None,
        "commentIdList": [],
        "hotelSemantic": None,
        "searchNodeInfo": None,
        "roomSelectedFilter": [],
        "traverlSelectedFilter": [],
        "languageSelectedFilter": [],
        "sortSelectedFilter": [],
        "keyword": "",
        "selectedImageOnlyTag": False,
        "selectedNegativeTag": False,
        "selectedTagId": None,
        "repeatComment": 1,
        "mainTabSelectedId": 1,
        "subTabSelectedId": -400,
        "rooms": [],
        "travelTypes": [],
        "filterDateTypeList": [],
        "orderTypes": [],
        "sceneAiSummaryFilterCommonId": None,
        "sceneAiSummaryFilterAiItemId": None,
        "negativeSummaryIssueTagId": None,
    }
    body = {"head": HEAD}
    body.update(biz)
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"))


def build_headers(body_str):
    tid = uuid.uuid4().hex
    return {
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
        # 埋点字段（风控方案：参数完整性，保留完整埋点）
        "x-ctx-ubt-vid": DEVICE["ubt_vid"],
        "x-ctx-ubt-pageid": "hotel_inland_comment_detail",
        "x-ctx-ubt-pvid": "1",
        "x-ctx-ubt-sid": "1",
        "Content-Type": "application/json;charset=utf-8",
    }


def sign_batch(md5_list):
    """批量签名（一次 RPC 拿多个签名），失败时重启 oracle 重试一次"""
    global script
    for attempt in range(2):
        try:
            return script.exports_sync.batch_sign(md5_list)
        except Exception as e:
            print(f"  [!] 签名失败（{e}），重启 oracle...", flush=True)
            start_oracle()
    return None


def fetch_page(url, body_str, sign):
    headers = build_headers(body_str)
    headers["x-payload-source"] = sign
    r = requests.post(url, data=body_str.encode("utf-8"), headers=headers, timeout=20)
    return r.status_code, r.text


def extract_comments(resp_text):
    """从响应提取 groupList[].commentList[] 的点评"""
    try:
        d = json.loads(resp_text)
    except Exception:
        return None, 0
    groups = d.get("groupList") or []
    comments = []
    for g in groups:
        cl = g.get("commentList") or []
        comments.extend(cl)
    total = d.get("totalCount") or 0
    return comments, total


def main():
    # 创建输出目录（每次运行新子目录，不覆盖）
    run_id = time.strftime("%Y%m%d_%H%M%S")
    out_dir = os.path.join(OUTPUT_ROOT, f"ctrip_438006_{run_id}")
    os.makedirs(out_dir, exist_ok=True)
    print(f"[*] 输出目录: {out_dir}", flush=True)

    device, session = start_oracle()
    url = "https://m.ctrip.com/restapi/soa2/24077/h5-json/clientHotelCommentList" + GW

    deadline = time.time() + DURATION_MINUTES * 60
    page_index = 1
    total_fetched = 0
    page_count = 0
    consecutive_fail = 0

    # 元信息文件
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as f:
        json.dump({"hotelId": HOTEL_ID, "hotelName": "昆明海丽宾雅万达嘉华温泉酒店",
                   "startTime": run_id, "durationMinutes": DURATION_MINUTES}, f, ensure_ascii=False)

    while time.time() < deadline:
        # 每批预生成 BATCH_SIGN_SIZE 页的 body + 签名
        batch_bodies = []
        batch_md5s = []
        for i in range(BATCH_SIGN_SIZE):
            b = build_body(page_index + i)
            batch_bodies.append(b)
            batch_md5s.append(hashlib.md5(b.encode("utf-8")).hexdigest().lower())

        signs = sign_batch(batch_md5s)
        if signs is None:
            print("[!] 签名 oracle 不可用，停止", flush=True)
            break

        # 逐页发送（拟人化随机间隔）
        for i in range(BATCH_SIGN_SIZE):
            if time.time() >= deadline:
                break
            pi = page_index + i
            st, txt = fetch_page(url, batch_bodies[i], signs[i])

            comments, total = extract_comments(txt)
            if st == 200 and comments:
                # 保存该页点评
                fname = os.path.join(out_dir, f"page_{pi:04d}.json")
                with open(fname, "w", encoding="utf-8") as f:
                    json.dump({"pageIndex": pi, "hotelId": HOTEL_ID,
                               "totalCount": total, "comments": comments}, f, ensure_ascii=False)
                page_count += 1
                total_fetched += len(comments)
                consecutive_fail = 0
                print(f"  page {pi}: {len(comments)} 条 (累计 {total_fetched} 条)", flush=True)
            elif st != 200:
                consecutive_fail += 1
                print(f"  page {pi}: status={st} 异常 (连续 {consecutive_fail} 次)", flush=True)
                if consecutive_fail >= 3:
                    print("[!] 连续异常，疑似频控/封禁，止损停止", flush=True)
                    break
            else:
                # 200 但无评论（可能翻页到底）
                consecutive_fail += 1
                print(f"  page {pi}: 无评论数据（total={total}）", flush=True)
                if total and len(comments) == 0:
                    print("[*] 翻页到底或蜜罐，停止", flush=True)
                    break

            # 拟人化随机间隔
            time.sleep(random.uniform(INTERVAL_MIN, INTERVAL_MAX))

        if consecutive_fail >= 3:
            break
        page_index += BATCH_SIGN_SIZE

    print(f"\n[*] 完成：共 {page_count} 页，{total_fetched} 条点评，输出 {out_dir}", flush=True)
    print(f"[*] meta: {out_dir}\\meta.json", flush=True)


if __name__ == "__main__":
    main()
