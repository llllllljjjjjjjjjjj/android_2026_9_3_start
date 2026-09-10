# -*- coding: utf-8 -*-
"""提取 A 方案拿到的真实搜索结果样例（视频列表）"""
import json, os

D = r"D:\reserve_agent\android\projects\dy\capture"
for name in ["resp_pottery_0_1789041438265.json", "resp_pottery_40_1789041438645.json"]:
    p = os.path.join(D, name)
    if not os.path.exists(p):
        continue
    raw = open(p, encoding="utf-8", errors="ignore").read()
    print(f"=== {name} ({len(raw)} B) ===")
    try:
        j = json.loads(raw)
    except Exception as e:
        print("  parse err", e)
        continue
    if isinstance(j, dict):
        print("  top keys:", list(j.keys())[:14])
        # 尝试常见视频列表容器
        def find_list(o, path="", depth=0):
            if depth > 4:
                return
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, list) and v and isinstance(v[0], dict) and (
                            "aweme_id" in v[0] or "desc" in v[0] or "statistics" in v[0]):
                        print(f"  VIDEO LIST at {path}.{k}: {len(v)} items")
                        it = v[0]
                        print(f"     sample keys: {list(it.keys())[:12]}")
                        if "desc" in it:
                            print(f"     desc: {str(it['desc'])[:80]}")
                        if "aweme_id" in it:
                            print(f"     aweme_id: {it['aweme_id']}")
                        return True
                    if isinstance(v, (dict, list)):
                        if find_list(v, f"{path}.{k}", depth + 1):
                            return True
            elif isinstance(o, list):
                for i, v in enumerate(o[:3]):
                    if isinstance(v, (dict, list)):
                        if find_list(v, f"{path}[{i}]", depth + 1):
                            return True
            return False
        find_list(j)
    print()
