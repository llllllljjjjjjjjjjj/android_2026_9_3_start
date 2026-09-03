# -*- coding: utf-8 -*-
# detail_param_rpc.py — RPC 返回抖音商品详情页「产品参数」
#
# 链路（App 代发，规避 PC 直发的 Cronet 指纹风控 hit_shark）：
#   0) force-stop + 冷启动抖音（清掉已释放的详情响应，确保深链触发新请求）
#   1) attach 抖音，挂 dy_hook_detail_param.js（内存扫描 qualification 锚点回溯）
#   2) mark() 记录内存基线（排除历史残留商品）
#   3) am start 深链 snssdk1128://ec_goods_detail?product_id=<id> 打开详情页
#   4) 用户手动滚动到产品信息卡，点开产品参数（弹出参数半屏，触发 attr 渲染）
#   5) 轮询 new() 拿到本次打开商品的产品参数 attr 对象
#   6) property_name_all / value 逗号对齐成对 → 有序 key:value 参数表
#
# 用法:
#   python detail_param_rpc.py                          # 默认样本商品
#   python detail_param_rpc.py --product-id <19位id>    # 任意商品
import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
HOOK = ROOT / "hooks" / "dy_hook_detail_param.js"
OUT_DIR = ROOT / "capture"

DEFAULT_PID = "3770115268144136255"  # 溪木源层孔菌精华水 230ml


def adb(*args):
    return subprocess.check_output([ADB, *args]).decode(errors="replace").strip()


def restart_app():
    subprocess.check_call([ADB, "shell", "am", "force-stop", PKG],
                          stdout=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.check_call([ADB, "shell", "monkey", "-p", PKG, "1"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(40)  # 等冷启动完成（metasec 初始化）


def attach():
    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pid = int(adb("shell", "pidof", PKG).split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    sess = dev.attach(pid)  # dy 反枚举隐藏进程表，adb pidof 直连 attach(pid)
    script = sess.create_script(HOOK.read_text(encoding="utf-8"))
    script.load()
    time.sleep(2)  # 让首轮 scan 稳定，mark 前缓存已覆盖历史残留
    return sess, script


def open_detail(product_id, deep_link):
    url = deep_link or f"snssdk1128://ec_goods_detail?product_id={product_id}"
    subprocess.check_call([ADB, "shell", "am", "start", "-a",
                           "android.intent.action.VIEW", "-d", url],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return url


def poll_new(script, timeout):
    deadline = time.time() + timeout
    last_note = 0
    while time.time() < deadline:
        try:
            out = script.exports_sync.new()
        except Exception as e:
            print("RPC new() fail:", e, flush=True)
            time.sleep(1)
            continue
        if out:
            return out
        now = time.time()
        if now - last_note >= 10:
            left = int(deadline - now)
            print(f"  等待产品参数弹层... 剩余 {left}s", flush=True)
            last_note = now
        time.sleep(1)
    return []


def parse_pairs(rec):
    names = rec.get("names", "").split(",")
    values = rec.get("values", "").split(",")
    n = min(len(names), len(values))
    pairs = [{"name": names[i], "value": values[i]} for i in range(n)]
    return pairs


def main():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--product-id", default=DEFAULT_PID)
    ap.add_argument("--deep-link", default="")
    ap.add_argument("--timeout", type=int, default=150,
                    help="等待你手动打开产品参数弹层的秒数")
    ap.add_argument("--no-fresh", action="store_true",
                    help="不重启 App（App 刚冷启动且已打开过详情页时用）")
    args = ap.parse_args()

    if not args.no_fresh:
        print("force-stop + 冷启动抖音（约 40s）...", flush=True)
        restart_app()
    else:
        print("跳过重启，直接 attach ...", flush=True)

    print("attach 抖音 ...", flush=True)
    sess, script = attach()
    print("hook loaded, mark 基线 ...", flush=True)
    base_cnt = script.exports_sync.mark()
    print("baseline attr objects:", base_cnt, flush=True)

    url = open_detail(args.product_id, args.deep_link)
    print("open detail:", url, flush=True)
    print("\n>>> 请在手机上手动打开该商品的产品参数弹层（产品信息卡内点开参数），"
          "脚本正在后台扫描等你操作...\n", flush=True)

    recs = poll_new(script, args.timeout)
    if not recs:
        print("FAIL: timeout，未捕获到产品参数。"
              "请确认已手动打开产品参数弹层（参数已显示在屏幕上）。",
              flush=True)
        sess.detach()
        sys.exit(1)

    rec = recs[-1]  # 最新一条
    print(f"\n[+] 捕获产品参数 attr_id={rec.get('attr_id')}", flush=True)
    print(f"    商品: {rec.get('title', '')}", flush=True)

    pairs = parse_pairs(rec)
    result = {
        "product_id": args.product_id,
        "attr_id": rec.get("attr_id"),
        "title": rec.get("title"),
        "params": {p["name"]: p["value"] for p in pairs},
        "params_ordered": pairs,
    }
    out = OUT_DIR / f"detail_param_{args.product_id}.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"    -> {out}\n", flush=True)

    print("产品参数（%d 项）:" % len(pairs), flush=True)
    for p in pairs:
        print(f"  {p['name']:<20} | {p['value']}", flush=True)

    sess.detach()


if __name__ == "__main__":
    main()
