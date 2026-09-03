# -*- coding: utf-8 -*-
# dy_oracle_collect.py — 八神签名 RPC oracle 批量采集（SF-012: 100+ 组随机输入）
# attach 到运行中 dy App → 加载 dy_hook21.js（纯 RPC）→ 分组批量调用 → JSON 落盘
# 分组（差分分析用）:
#   G1 同一输入重复 6 次          → 时间依赖性（Khronos 抖动 / 随机盐）
#   G2 固定 headers, url 单字符变化 20 组
#   G3 固定 url, headers 单字符变化 20 组
#   G4 完全随机组合 40 组
#   G5 空输入/边界 6 组
#   G6 真实遥测 URL + cookie 变体 20 组
import json, random, string, sys, time
import frida

DEVICE = "127.0.0.1:27042"
PKG = "com.ss.android.ugc.aweme"
HOOK = r"D:\reserve_agent\skills-portable-test\projects\dy\hooks\dy_hook21.js"
OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\capture\oracle_dataset.json"

RND = random.Random(0x8BADF00D)

def rand_str(n, pool=string.ascii_letters + string.digits):
    return "".join(RND.choice(pool) for _ in range(n))

BASE_URL = "https://log0-misc-lf.amemv.com/service/2/app_log/performance/p2/?version_code=380000&device_platform=android&device_id=2310516478094584&aid=1128&iid=305014557150939&app_log_priority=2128144&tt_data=a"
BASE_HDR = "cookie\r\npassport_csrf_token=441f7e5260f91551c264fe7e4ac152d8\r\nuser-agent\r\ncom.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001)\r\naccept-encoding\r\ngzip, deflate, br"

def build_groups():
    g = {}
    # G1 同一输入重复
    g["G1_repeat"] = [{"u": BASE_URL, "h": BASE_HDR} for _ in range(6)]
    # G2 url 单字符变化（在 query 值里逐位翻转 device_id）
    g2 = []
    for i in range(20):
        u = BASE_URL.replace("device_id=2310516478094584",
                             "device_id=" + rand_str(16, string.digits))
        g2.append({"u": u, "h": BASE_HDR})
    g["G2_url_var"] = g2
    # G3 headers 单字符变化（cookie 值变化 + 追加随机头）
    g3 = []
    for i in range(20):
        h = BASE_HDR.replace("passport_csrf_token=441f7e5260f91551c264fe7e4ac152d8",
                             "passport_csrf_token=" + rand_str(32)) + \
            "\r\nx-rand\r\n" + rand_str(12)
        g3.append({"u": BASE_URL, "h": h})
    g["G3_hdr_var"] = g3
    # G4 完全随机
    g4 = []
    paths = ["/service/2/app_log/performance/p2/", "/service/2/app_log/",
             "/aweme/v1/feed/", "/aweme/v1/aweme/post/", "/service/1/device/register/"]
    for i in range(40):
        u = "https://log0-misc-lf.amemv.com" + RND.choice(paths) + \
            "?aid=1128&device_id=" + rand_str(16, string.digits) + \
            "&iid=" + rand_str(15, string.digits) + "&extra=" + rand_str(8)
        h = BASE_HDR.replace("passport_csrf_token=441f7e5260f91551c264fe7e4ac152d8",
                             "passport_csrf_token=" + rand_str(32)) + \
            "\r\nx-body-md5\r\n" + rand_str(32, "0123456789abcdef")
        g4.append({"u": u, "h": h})
    g["G4_random"] = g4
    # G5 边界
    g["G5_edge"] = [
        {"u": "", "h": ""},
        {"u": BASE_URL, "h": ""},
        {"u": "", "h": BASE_HDR},
        {"u": "https://x/", "h": "a\r\nb\r\nc\r\nd"},
        {"u": BASE_URL + "&x=" + "A" * 2000, "h": BASE_HDR},
        {"u": "not-a-url", "h": BASE_HDR},
    ]
    # G6 真实遥测 URL + cookie 变体
    g6 = []
    real_cookie = "passport_csrf_token=441f7e5260f91551c264fe7e4ac152d8; store-region=cn-jx; install_id=305014557150939; ttreq=1$acc983328eca331511c6dc5dd3f013547253a032; odin_tt=32aad904d8b4f9885148b901fa0bafb3b3920f9d1652c08f8989dd5b3890209ab978eb52877f098d8e0f7624785eed182384758048bca5ad300326bfdf5e9c0c353e513a1b94c97e4ab6030b33a38823"
    for i in range(20):
        c = "passport_csrf_token=" + rand_str(32) + "; store-region=cn-jx; install_id=305014557150939; ttreq=1$" + rand_str(40) + "; odin_tt=" + rand_str(200)
        h = "cookie\r\n" + c + "\r\nuser-agent\r\ncom.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; Build/QQ3A.200605.001)"
        g6.append({"u": BASE_URL, "h": h})
    g["G6_real_cookie_var"] = g6
    return g

def get_pid_via_adb():
    import subprocess
    adb = r"D:\reserve_agent\skills-portable-test\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
    subprocess.check_call([adb, "forward", "tcp:27042", "tcp:27042"])
    out = subprocess.check_output([adb, "shell", "pidof", PKG]).decode().strip()
    if not out:
        raise RuntimeError("pidof empty: app not running")
    return int(out.split()[0])

def main():
    dev = frida.get_device_manager().add_remote_device(DEVICE)
    print("[*] device ok")
    # App 反枚举（frida 进程表不可见）→ 用 adb pidof 拿 pid 直连
    pid = get_pid_via_adb()
    print("[*] pid=%d, attaching..." % pid)
    session = dev.attach(pid)
    with open(HOOK, "r", encoding="utf-8") as f:
        js = f.read()
    script = session.create_script(js)
    def on_msg(m, d):
        print("[msg]", m.get("type"), m.get("payload"))
    script.on("message", on_msg)
    script.load()
    time.sleep(2)
    print("[*] base =", script.exports_sync.getbase())

    groups = build_groups()
    total = sum(len(v) for v in groups.values())
    print("[*] %d groups, %d inputs total" % (len(groups), total))

    # 先 3 组试探（RPC 线程上下文安全性）
    probe = [{"u": BASE_URL, "h": BASE_HDR}] * 3
    try:
        res = script.exports_sync.oraclebatch(probe)
        print("[*] probe ok:", res[0]["ms"], "ms, first 80 chars:", res[0]["o"][:80])
    except Exception as e:
        print("[!] probe FAILED:", e)
        session.detach()
        sys.exit(1)

    # 全量采集
    dataset = {"ts": int(time.time()), "pkg": PKG, "groups": {}}
    for gname, arr in groups.items():
        print("[*] collecting %s (%d)..." % (gname, len(arr)))
        res = script.exports_sync.oraclebatch(arr)
        ok = sum(1 for r in res if (r.get("o") or "").startswith("X-"))
        print("    ok=%d/%d" % (ok, len(arr)))
        dataset["groups"][gname] = {"inputs": arr, "results": res}
        time.sleep(0.5)

    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=1)
    print("[*] dataset saved:", OUT)
    session.detach()

if __name__ == "__main__":
    main()
