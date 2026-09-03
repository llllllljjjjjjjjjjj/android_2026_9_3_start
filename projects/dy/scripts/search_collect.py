# -*- coding: utf-8 -*-
# search_collect.py — 抖音搜索采集器（内存扫描 aweme_info，直取完整视频字段）
#
# ★ 核心机制（2026-08-28 定稿）：
#   - 搜索响应的 aweme_info（视频 id/标题/作者/统计）在 libsscronet **native 层**用
#     C++ JSON 解析（nlohmann/json），不走 Java 的 org.json/gson → Java hook 抓不到。
#   - 本采集器改用 **内存扫描**：触发搜索后，Memory.scanSync 搜 "aweme_info" 字符串，
#     回溯 JSON 开头，dump 完整片段 → 精确拿到 aweme_id/desc/author/statistics。
#
# 用法:
#   python search_collect.py --kws 美食,火锅 --limit 5
#   python search_collect.py --kws 露营 --limit 10
#
# 依赖：真机 App 运行 + florida-server + adb + frida（.venv-frida-16.5.7）
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import frida

ROOT = Path(__file__).resolve().parents[1]
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
PKG = "com.ss.android.ugc.aweme"
OUT = ROOT / "capture" / "search_collect_result.json"

# 内存扫描 aweme_info 的 JS（替代 Java JSON hook）
JS = r'''
var sent = {};
function scan() {
  var ranges = Process.enumerateRanges("r--");
  ranges.forEach(function (r) {
    try {
      if (r.size < 4096 || r.size > 256 * 1024 * 1024) return;
      var res = Memory.scanSync(r.base, r.size, "61 77 65 6d 65 5f 69 6e 66 6f");  // "aweme_info"
      res.forEach(function (m) {
        // 回溯找 JSON 开头 '{'
        var p = m.address, start = p;
        for (var i = 0; i < 2048; i++) {
          var q = p.sub(i);
          try { if (q.readU8() === 0x7b) { start = q; break; } } catch (e) { break; }
        }
        try {
          // 读尽量长的 JSON 片段（aweme_info 完整结构可能 >2KB）
          var s = start.readUtf8String(8000);
          if (s.indexOf("aweme_id") < 0 || s.indexOf("desc") < 0) return;
          var key = s.slice(0, 60);
          if (sent[key]) return;
          sent[key] = true;
          send({ t: "aweme", body: s });
        } catch (e) {}
      });
    } catch (e) {}
  });
}
setInterval(scan, 1000);
'''


def collect_search(keywords, limit):
    """逐词: 挂内存扫描 hook → 触发搜索 → 解析 aweme_info 完整字段。"""
    # 重启 App 清空内存残留（避免扫到历史搜索的 aweme_info）
    subprocess.check_call([ADB, "shell", "am", "force-stop", PKG], stdout=subprocess.DEVNULL)
    time.sleep(2)
    subprocess.check_call([ADB, "shell", "monkey", "-p", PKG, "1"],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(45)  # 等冷启动完成

    subprocess.check_call([ADB, "forward", "tcp:27042", "tcp:27042"])
    pid = int(subprocess.check_output([ADB, "shell", "pidof", PKG]).decode().split()[0])
    dev = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    sess = dev.attach(pid)
    script = sess.create_script(JS)

    awemes = {}  # aweme_id -> info（去重，保序）
    order = []

    def on_msg(msg, data):
        p = msg.get("payload")
        if isinstance(p, dict) and p.get("t") == "aweme":
            parse_aweme_fragment(p["body"])

    def parse_aweme_fragment(s):
        # 正则提取关键字段（不依赖完整 JSON 解析，避免 8000 字符截断导致 json.loads 失败）
        for m in re.finditer(r'"aweme_id":"(\d{15,20})"', s):
            aid = m.group(1)
            if aid in awemes:
                continue
            pos = m.end()
            tail = s[pos:pos + 12000]
            desc_m = re.search(r'"desc":"((?:[^"\\]|\\.)*)"', tail)
            nick_m = re.search(r'"nickname":"((?:[^"\\]|\\.)*)"', tail)
            uid_m = re.search(r'"uid":"(\d+)"', tail)
            digg_m = re.search(r'"digg_count":(\d+)', tail)
            cmt_m = re.search(r'"comment_count":(\d+)', tail)
            coll_m = re.search(r'"collect_count":(\d+)', tail)
            awemes[aid] = {
                "aweme_id": aid,
                "title": (desc_m.group(1) if desc_m else "")[:300],
                "author": nick_m.group(1) if nick_m else "",
                "author_uid": uid_m.group(1) if uid_m else "",
                "likes": digg_m.group(1) if digg_m else "",
                "comments": cmt_m.group(1) if cmt_m else "",
                "collects": coll_m.group(1) if coll_m else "",
                "plays": "",
                "create_time": "",
            }
            order.append(aid)

    script.on("message", on_msg)
    script.load()
    time.sleep(8)  # 让 scan 完整扫一遍启动期首页 feed，记入 order（不计入结果）

    results = []
    for kw in keywords:
        before = len(order)  # 触发前快照（排除启动期/历史残留）
        subprocess.check_call([ADB, "shell", "am", "start", "-a", "android.intent.action.VIEW",
                               "-d", "snssdk1128://search?keyword=" + kw])
        time.sleep(15)  # 等响应到达 + native 解析
        for aid in order[before:]:
            info = awemes[aid]
            if not info.get("keyword"):
                info["keyword"] = kw
                results.append(info)
        print(f"[{kw}] 抓到 {len(order) - before} 条 aweme_info", flush=True)
        time.sleep(3)
    sess.detach()
    return results


def main():
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    ap = argparse.ArgumentParser()
    ap.add_argument("--kws", default="美食,火锅")
    ap.add_argument("--limit", type=int, default=10, help="每个词最多取几条")
    args = ap.parse_args()

    kws = [k.strip() for k in args.kws.split(",") if k.strip()]
    results = collect_search(kws, args.limit)
    # 每个词限制条数
    limited = []
    cnt = {}
    for r in results:
        k = r.get("keyword", "")
        if cnt.get(k, 0) >= args.limit:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        limited.append(r)
    OUT.write_text(json.dumps(limited, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完成: {len(limited)} 条 → {OUT}")
    for r in limited:
        print(f"  - [{r.get('keyword')}] {r.get('title','')[:40]} | 作者:{r.get('author')} "
              f"| 赞:{r.get('likes')} 评:{r.get('comments')} | id:{r.get('aweme_id')}")


if __name__ == "__main__":
    main()
