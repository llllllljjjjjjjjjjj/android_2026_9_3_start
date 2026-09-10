# -*- coding: utf-8 -*-
"""修正 SKILL.md 工作流顺序：A → B → C → D"""
import re

P = r"D:\reserve_agent\android\.dsh\skills\risk-control-adversary\SKILL.md"
t = open(P, encoding="utf-8").read()
open(P + ".bak-order", "w", encoding="utf-8").write(t)

# 定位各工作流区块
mD = t.find("## 工作流 D：单接口全链路风控分析")
mC = t.find("## 工作流 C：风控体系评估")
mExt = t.find("## 扩展协议")

if not (0 < mD < mC < mExt):
    print("边界异常，放弃")
    raise SystemExit(1)

blockD = t[mD:mC]      # D 区块（含尾部空行）
blockC = t[mC:mExt]    # C 区块
# 重排：C 在前，D 在后
t2 = t[:mD] + blockC + blockD + t[mExt:]

open(P, "w", encoding="utf-8").write(t2)

# 校验
chk = open(P, encoding="utf-8").read()
order = [(m.group(1), m.start()) for m in re.finditer(r"^## 工作流 ([A-Z])：", chk, re.M)]
print("工作流顺序:", [x[0] for x in order])
print("正确:", [x[0] for x in order] == ["A", "B", "C", "D"])
