# -*- coding: utf-8 -*-
"""校验重写后的 flow-and-risk.md 结构"""
import re

p = r"D:\reserve_agent\android\projects\dy\docs\flow-and-risk.md"
t = open(p, encoding="utf-8").read()

print("行数:", t.count("\n") + 1, "| 字节:", len(t.encode("utf-8")))
print()
print("=== 章节结构 ===")
for m in re.finditer(r"^## .*", t, re.M):
    print("  " + m.group(0)[:62])

print()
print("=== 模板要素自检 ===")
checks = [
    ("三段时序(前/中/后)", "前 / 中 / 后" in t),
    ("逐笔参数快照", "可复刻参数快照" in t),
    ("数据依赖链", "数据依赖链" in t),
    ("服务端凭证(authentication_token)", "authentication_token" in t),
    ("本地复刻规格", "本地复刻规格" in t),
    ("访问序列", "访问序列" in t),
    ("复刻要点表", "复刻要点表" in t),
    ("本地实现检查清单", "本地实现检查清单" in t),
    ("配对关系", "配对" in t),
    ("降级判据", "降级判据" in t),
    ("待验证实验清单", "待验证实验清单" in t),
    ("验收标准句", "无需回头问" in t),
]
for name, ok in checks:
    print(f"  {name:32s}: {'OK' if ok else 'MISSING'}")

print()
print("缺证据标注 [未证]/[未知]/[未做]:", len(re.findall(r"\[(未证|未知|未做)\]", t)))
print("出现 '推测' 次数:", t.count("推测"))
print("出现 '已实证' 次数:", t.count("已实证"))
print("出现 '阻断' 次数:", t.count("阻断"))

# 与旧版对比
old = open(p + ".bak-old", encoding="utf-8").read()
print()
print("=== 新旧对比 ===")
print(f"  旧版: {old.count(chr(10))+1} 行 / {len(old.encode('utf-8'))} 字节")
print(f"  新版: {t.count(chr(10))+1} 行 / {len(t.encode('utf-8'))} 字节")
for kw in ["数据依赖链", "本地复刻规格", "前 / 中 / 后", "检查清单", "验收标准", "七层"]:
    ino = kw in old
    inn = kw in t
    print(f"  {kw:16s}: 旧={ino} 新={inn}")
