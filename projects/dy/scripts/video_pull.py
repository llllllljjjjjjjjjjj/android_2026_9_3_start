# -*- coding: utf-8 -*-
"""通过 aid 拿视频/图文：元数据 + 播放地址/图片地址（可选下载）

用法:
  python video_pull.py <aid> [more_aids...]
  python video_pull.py --from results_hiking.json 5
  python video_pull.py --download <aid>...        # 视频 mp4 / 图文 多图
"""
import sys, json, time, subprocess, os, urllib.request, urllib.error
import frida
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import risk_health as rh

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_video_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"
DLDIR = os.path.join(OUTDIR, "videos")
UA = ("com.ss.android.ugc.aweme/380001 (Linux; U; Android 10; zh_CN_#Hans; Pixel 4; "
      "Build/QQ3A.200605.001; Cronet/TTNetVersion:0fa322de 2024-11-06)")
HEADERS = {"User-Agent": UA, "Referer": "https://www.douyin.com/"}

# 视频 CDN 特征（用于从 url_list 里优选真正的视频地址）
VIDEO_HOSTS = ("douyinvod.com", "douyinpic.com/video", "aweme.snssdk.com/aweme/v1/play",
               "vod", "bytevcloudvod", "ixigua")
# 音乐/静态资源域名（图文背景音常落这里，需排除）
MUSIC_HOSTS = ("douyinstatic.com", "douyinmusic", "/music")


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def attach_script(retries=3):
    for i in range(retries):
        try:
            dev = frida.get_device_manager().add_remote_device(HOST)
            pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
            session = dev.attach(int(pid[0])) if pid else dev.attach(PKG)
            script = session.create_script(open(JS, encoding="utf-8").read())
            script.on("message", lambda m, d: None)
            script.load()
            time.sleep(0.6)
            return session, script
        except Exception as e:
            print(f"[!] attach {i+1}/{retries} failed: {e}")
            time.sleep(3 * (i + 1))
    return None, None


def pick_video_url(urls):
    """从 url_list 优选视频地址（避开 music/static 等相邻字段）"""
    if not urls:
        return None
    for u in urls:
        if any(h in u for h in VIDEO_HOSTS) and not any(m in u for m in MUSIC_HOSTS):
            return u
    for u in urls:                      # 兜底：排除音乐域名
        if not any(m in u for m in MUSIC_HOSTS):
            return u
    return urls[0]


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def sniff_ext(data):
    """按 magic 判定真实扩展名（抖音图片可能是 HEIF/VVC，勿写死 .jpg）"""
    if data[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if data[:4] == b"\x89PNG":
        return ".png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    if data[4:8] == b"ftyp":
        brand = data[8:12]
        if brand in (b"heic", b"heix", b"mif1", b"vvic", b"avif"):
            return ".heic"
        return ".bin"
    if data[:5] == b"GIF8":
        return ".gif"
    return ".bin"


def download(rec):
    """按 mediaType 分流下载；任何异常都只告警，不中断"""
    aid = rec.get("aid") or "unknown"
    mt = rec.get("mediaType") or "unknown"
    os.makedirs(DLDIR, exist_ok=True)

    if mt == "video":
        urls = rec.get("playUrl") or []
        if not urls:
            print(f"[!] {aid}: video 但无 playUrl，跳过")
            return 0
        url = pick_video_url(urls)
        out = os.path.join(DLDIR, f"{aid}.mp4")
        if os.path.exists(out) and os.path.getsize(out) > 1024:
            print(f"[=] {aid}: 已存在，跳过")
            return 0
        try:
            data = fetch(url)
            open(out, "wb").write(data)
            ok = b"ftyp" in data[:32]
            print(f"[*] {aid} video -> {os.path.basename(out)} ({len(data)} B) mp4={ok}")
            return 1
        except urllib.error.HTTPError as e:
            print(f"[!] {aid}: HTTP {e.code} 下载失败（URL 可能已过期，需重新获取）")
        except Exception as e:
            print(f"[!] {aid}: 下载失败 {type(e).__name__} {e}")
        return 0

    if mt == "album":
        pics = rec.get("imageUrl") or []
        if not pics:
            print(f"[!] {aid}: album 但无图片地址，跳过")
            return 0
        ok = 0
        for i, u in enumerate(pics, 1):
            try:
                data = fetch(u, timeout=30)
            except Exception as e:
                print(f"[!] {aid} img{i}: {type(e).__name__} {e}")
                continue
            ext = sniff_ext(data)
            out = os.path.join(DLDIR, f"{aid}_img{i:02d}{ext}")
            # 已存在同图（任意扩展名）则跳过
            if any(os.path.exists(os.path.join(DLDIR, f"{aid}_img{i:02d}{e}"))
                   for e in (".jpg", ".png", ".webp", ".heic", ".bin")):
                ok += 1
                continue
            open(out, "wb").write(data)
            ok += 1
            if ext in (".bin", ".heic"):
                print(f"[!] {aid} img{i}: 非常规格式 {ext}（抖音 HEIF/VVC 原图，兼容性有限）")
        print(f"[*] {aid} album -> {ok}/{len(pics)} 张图片")
        return ok

    print(f"[!] {aid}: mediaType={mt}（无可用媒体地址）")
    return 0


def main():
    args = sys.argv[1:]
    do_dl = False
    if "--download" in args:
        do_dl = True
        args.remove("--download")

    aids = []
    if args and args[0] == "--from":
        src = os.path.join(OUTDIR, args[1])
        n = int(args[2]) if len(args) > 2 else 3
        data = json.load(open(src, encoding="utf-8"))
        aids = [c["aid"] for c in data[:n] if c.get("aid")]
    else:
        aids = [a for a in args if a.isdigit()]

    if not aids:
        print("usage: video_pull.py <aid>... | --from <results_x.json> [n] | --download <aid>")
        return 1

    session, script = attach_script()
    if not session:
        print("[!] abort: cannot attach")
        return 1
    try:
        script.exports_sync.clear()
        health = rh.RiskHealth("video")
        for i, aid in enumerate(aids, 1):
            script.exports_sync.openurl(f"snssdk1128://aweme/detail/{aid}")
            time.sleep(7)
            print(f"[*] {i}/{len(aids)} aid={aid}, collected={script.exports_sync.count()}")
            if i < len(aids):
                adb("shell", "input", "keyevent", "4")
                time.sleep(1.5)

        # ★ 风控健康检查（视频链路核心：detail 前置 + stats 播放上报）
        for u in (script.exports_sync.getpaths() or []):
            health.note(u)
        print()
        print(health.report())

        data = script.exports_sync.getlist()

        # ★ 降级判官
        if not data:
            verdict, detail = "soft", "未采集到媒体信息"
        else:
            with_url = sum(1 for v in data if (v.get("playUrl") or v.get("imageUrl")))
            if with_url == 0:
                verdict, detail = "soft", "无可用媒体地址（可能已过期或降级）"
            else:
                verdict, detail = "ok", "含媒体地址"
        ok = rh.print_verdict(verdict, detail, len(data))

        out = os.path.join(OUTDIR, "videos.json")
        json.dump({"verdict": verdict, "count": len(data),
                   "riskHealth": health.report(), "media": data},
                  open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

        # 统计（容错：类型缺失时归入 unknown）
        stat = {}
        for v in data:
            stat[v.get("mediaType", "unknown")] = stat.get(v.get("mediaType", "unknown"), 0) + 1
        print(f"[*] media: {len(data)} -> {out}  {stat}")
        for v in data[:8]:
            mt = v.get("mediaType")
            first = (v.get("playUrl") or v.get("imageUrl") or ["<none>"])[0]
            print(f"    [{mt}] aid={v['aid']} awemeType={v.get('awemeType')} "
                  f"imgs={v.get('imageCount')} {str(v.get('desc') or '')[:30]}")
            print(f"        {first[:100]}")

        if do_dl:
            total = fails = 0
            for v in data:
                try:
                    total += download(v)
                except Exception as e:      # 兜底：绝不让单个条目中断批量
                    fails += 1
                    print(f"[!] {v.get('aid')}: unexpected {type(e).__name__} {e}")
            print(f"[*] downloaded files: {total}, unexpected errors: {fails}")
        return 0
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
