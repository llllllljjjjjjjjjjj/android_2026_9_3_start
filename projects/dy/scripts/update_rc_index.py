# -*- coding: utf-8 -*-
"""更新 risk-control-adversary 的项目索引：追加 dy 项目"""
import os

P = r"D:\reserve_agent\android\.dsh\skills\risk-control-adversary\references\projects\_index.md"

txt = open(P, encoding="utf-8").read()
print("=== 当前内容 ===")
print(txt)
print("=== 检查 dy ===", "dy" in txt.split("\n|")[0:1] or "| dy " in txt)

if "| dy " in txt:
    print("dy 已存在，跳过")
else:
    row = ("| dy | projects/dy.md | projects/dy/docs/risk-control-plan.md | Android | "
           "实验阶段（搜索/视频/评论链路已通；完整签名头已抓取；响应体应用层加密未解） | 2026-09-10 |")
    if not txt.endswith("\n"):
        txt += "\n"
    txt += row + "\n"
    open(P, "w", encoding="utf-8").write(txt)
    print("已追加 dy 行")
    print(open(P, encoding="utf-8").read())
