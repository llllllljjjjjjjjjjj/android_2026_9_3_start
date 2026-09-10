# -*- coding: utf-8 -*-
import re

SK = r"D:\reserve_agent\android\.dsh\skills\risk-control-adversary\SKILL.md"
TP = r"D:\reserve_agent\android\.dsh\skills\risk-control-adversary\references\templates.md"
s = open(SK, encoding="utf-8").read()
t = open(TP, encoding="utf-8").read()
d = s[s.find("## 工作流 D"):s.find("## 扩展协议")]

print("=== 最终状态 ===")
print("SKILL.md:", s.count("\n") + 1, "行 | templates.md:", t.count("\n") + 1, "行")
print("工作流:", [m.group(1) for m in re.finditer(r"^## 工作流 ([A-Z])：", s, re.M)])
print()

print("=== 你提的严谨性问题是否解决 ===")
checks = [
    ("证据证明(来源+路径)", ("D0.1" in d) and ("D0.4" in d)),
    ("证据等级(全局要求)", d.count("证据等级") >= 8),
    ("稳定性判据", "D1.1 稳定性判据" in d),
    ("轮次不一致处理", "D1.2 轮次不一致时的处理" in d),
    ("参数来源第四类(未知)", "D2.1 参数来源四分类" in d),
    ("降级判据自身要证据", "D6.1 降级判据本身也要有证据" in d),
    ("验收三条件(含无幻觉)", "无幻觉" in d),
    ("因果门槛(推测)", "证据等级只能标「推测」" in d or "证据等级最高只能标「推测」" in d),
]
for name, ok in checks:
    print("  " + name.ljust(24) + ": " + ("OK" if ok else "缺"))

print()
s25 = t[t.find("## §2.5"):t.find("## §2 项目风控记录模板")]
print("=== templates §2.5 ===")
print("  表格含证据等级:", s25.count("证据等级"), "处")
print("  含证据纪律:", "证据纪律" in s25)
print("  含来源四分类:", "来源四分类" in s25)
print("  含判据来源要求:", "判据来源要求" in s25)
