# -*- coding: utf-8 -*-
"""核对 flow-and-risk.md 规格 与 现有采集脚本的一致性
检查脚本是否遗漏了规格要求的：前置接口 / 配套上报 / 串行依赖 / 降级判官
"""
import re, os

SC = r"D:\reserve_agent\android\projects\dy\scripts"
spec = open(r"D:\reserve_agent\android\projects\dy\docs\flow-and-risk.md", encoding="utf-8").read()

# 规格要求的配套请求
REQUIRED = {
    "搜索前置": "history_words_record",
    "搜索紧邻上报": "upload_ei_feature",
    "评论前置": "aweme/detail",
    "评论紧邻上报": "app_log",
    "视频紧邻上报": "aweme/stats",
}

targets = ["search_rpc.py", "comment_rpc.py", "video_pull.py", "risk_health.py"]

print("=== 脚本中是否出现规格要求的接口 ===\n")
print(f"{'脚本':18s} " + " ".join(f"{k:10s}" for k in REQUIRED))
print("-" * 78)
for fn in targets:
    p = os.path.join(SC, fn)
    if not os.path.exists(p):
        continue
    t = open(p, encoding="utf-8").read()
    marks = []
    for k, kw in REQUIRED.items():
        marks.append("✓" if kw in t else "✗")
    print(f"{fn:18s} " + " ".join(f"{m:10s}" for m in marks))

print("\n=== risk_health.py 是否覆盖规格的降级判据 ===")
rh = open(os.path.join(SC, "risk_health.py"), encoding="utf-8").read()
for k in ["-99999", "has_more", "category_list", "软降级", "硬拒绝", "judge_response"]:
    print(f"  {k:16s}: {'✓' if k in rh else '✗'}")

print("\n=== 脚本是否检查『前置依赖』（规格 §三 数据依赖链）===")
cr = open(os.path.join(SC, "comment_rpc.py"), encoding="utf-8").read()
for k in ["aweme_author", "comment_count", "authentication_token", "detail"]:
    print(f"  comment_rpc.py 含 {k:22s}: {'✓' if k in cr else '✗'}")
sr = open(os.path.join(SC, "search_rpc.py"), encoding="utf-8").read()
for k in ["history_words", "upload_ei_feature", "search_id"]:
    print(f"  search_rpc.py  含 {k:22s}: {'✓' if k in sr else '✗'}")
