# -*- coding: utf-8 -*-
"""列出 D 内所有表格，标出缺证据列的"""
import re

t = open(r"D:\reserve_agent\android\.dsh\skills\risk-control-adversary\SKILL.md",
         encoding="utf-8").read()
d = t[t.find("## 工作流 D"):t.find("## 扩展协议")]

lines = d.split("\n")
i = 0
n = 0
while i < len(lines):
    if lines[i].startswith("|") and i + 1 < len(lines) and re.match(r"^\|[-| ]+\|$", lines[i + 1].strip()):
        # 收集整张表
        block = [lines[i]]
        j = i + 1
        while j < len(lines) and lines[j].startswith("|"):
            block.append(lines[j])
            j += 1
        n += 1
        has_ev = "证据等级" in "".join(block)
        flag = "OK  " if has_ev else "MISS"
        print(f"{n}. [{flag}] 行{i+1:4d}  {lines[i][:88]}")
        i = j
    else:
        i += 1
