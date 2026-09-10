# -*- coding: utf-8 -*-
"""校验 A 方案落盘的响应是否为真实搜索结果"""
import json, glob, os, sys

D = r"D:\reserve_agent\android\projects\dy\capture"
files = sorted(glob.glob(os.path.join(D, "resp_pottery_*.json")), key=os.path.getsize, reverse=True)

for f in files[:6]:
    raw = open(f, encoding="utf-8", errors="ignore").read()
    name = os.path.basename(f)
    print(f"=== {name} ({len(raw)} B) ===")
    try:
        j = json.loads(raw)
        if isinstance(j, dict):
            keys = list(j.keys())
            print("  top keys:", keys[:18])
            # 找数据主体
            for k in ("data", "aweme_list", "doc_dict", "card_list", "business_data", "log_pb", "search_id", "global_doodle_config"):
                if k in j:
                    v = j[k]
                    if isinstance(v, list):
                        print(f"  {k}: list len={len(v)}")
                    elif isinstance(v, dict):
                        print(f"  {k}: dict keys={list(v.keys())[:10]}")
                    else:
                        print(f"  {k} = {str(v)[:120]}")
        elif isinstance(j, list):
            print("  top-level list len:", len(j))
            if j:
                print("  first item keys:", list(j[0].keys())[:15] if isinstance(j[0], dict) else type(j[0]))
    except Exception as e:
        print("  json parse err:", e, "| head:", raw[:200])
    print()
