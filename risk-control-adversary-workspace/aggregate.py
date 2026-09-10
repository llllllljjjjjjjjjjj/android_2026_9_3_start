# -*- coding: utf-8 -*-
"""生成 timing.json（本环境子代理不可用，由主代理代跑，token/时间无法精确计）
   与 benchmark.json（聚合两个配置的 pass_rate）
"""
import json, os, glob

IT = r"D:\reserve_agent\android\risk-control-adversary-workspace\iteration-1"

# 本环境：subagent 不可用 → 由主代理在同一会话代跑，无法取得子代理级 token/timing
# 按 skill-creator 要求留 timing.json，但如实标注来源
for name in ["search-chain-fullflow", "comment-chain-fullflow", "risk-points-scan"]:
    for ver in ["with_skill", "old_skill"]:
        d = os.path.join(IT, name, ver)
        if not os.path.isdir(d):
            continue
        tp = os.path.join(d, "timing.json")
        if not os.path.exists(tp):
            json.dump({
                "total_tokens": None,
                "duration_ms": None,
                "total_duration_seconds": None,
                "note": "本环境 subagent 工具不可用（全部 spawn 失败），由主代理在同一会话代跑，无子代理级 token/timing 数据"
            }, open(tp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# 聚合
rows = []
for g in sorted(glob.glob(os.path.join(IT, "*", "*", "grading.json"))):
    j = json.load(open(g, encoding="utf-8"))
    rows.append(j)

by_name = {}
for r in rows:
    by_name.setdefault(r["eval_name"], {})[r["configuration"]] = r

summary = {"iteration": 1, "skill_name": "risk-control-adversary", "results": []}
for name, cfgs in by_name.items():
    w = cfgs.get("with_skill", {})
    o = cfgs.get("old_skill", {})
    summary["results"].append({
        "eval_name": name,
        "with_skill": {"pass_rate": w.get("pass_rate"), "passed": w.get("passed"), "total": w.get("total")},
        "old_skill": {"pass_rate": o.get("pass_rate"), "passed": o.get("passed"), "total": o.get("total")},
        "delta": round((w.get("pass_rate") or 0) - (o.get("pass_rate") or 0), 3),
        "expectations_diff": [
            {"text": we["text"], "with_skill": we["passed"],
             "old_skill": next((oe["passed"] for oe in o.get("expectations", []) if oe["text"] == we["text"]), None)}
            for we in w.get("expectations", [])
        ],
    })

# 总平均
ws = [r["with_skill"]["pass_rate"] for r in summary["results"] if r["with_skill"]["pass_rate"] is not None]
os_ = [r["old_skill"]["pass_rate"] for r in summary["results"] if r["old_skill"]["pass_rate"] is not None]
summary["aggregate"] = {
    "with_skill_mean": round(sum(ws) / len(ws), 3) if ws else None,
    "old_skill_mean": round(sum(os_) / len(os_), 3) if os_ else None,
    "mean_delta": round((sum(ws) / len(ws)) - (sum(os_) / len(os_)), 3) if ws and os_ else None,
    "note": "无子代理级 token/timing 数据（subagent 不可用）",
}

json.dump(summary, open(os.path.join(IT, "benchmark.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# markdown 版
lines = ["# benchmark — risk-control-adversary（iteration 1）", ""]
lines.append("| 用例 | with_skill | old_skill | delta |")
lines.append("|---|---|---|---|")
for r in summary["results"]:
    lines.append(f"| {r['eval_name']} | {r['with_skill']['pass_rate']} "
                 f"({r['with_skill']['passed']}/{r['with_skill']['total']}) | "
                 f"{r['old_skill']['pass_rate']} ({r['old_skill']['passed']}/{r['old_skill']['total']}) | "
                 f"+{r['delta']} |")
a = summary["aggregate"]
lines.append("")
lines.append(f"**均值**：with_skill {a['with_skill_mean']} vs old_skill {a['old_skill_mean']} "
             f"（delta +{a['mean_delta']}）")
lines.append("")
lines.append("## 逐断言差异")
lines.append("")
for r in summary["results"]:
    lines.append(f"### {r['eval_name']}")
    lines.append("")
    lines.append("| 断言 | with_skill | old_skill |")
    lines.append("|---|---|---|")
    for d in r["expectations_diff"]:
        lines.append(f"| {d['text']} | {'✓' if d['with_skill'] else '✗'} | "
                     f"{'✓' if d['old_skill'] else '✗'} |")
    lines.append("")

open(os.path.join(IT, "benchmark.md"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines[:14]))
print(f"\n-> {IT}\\benchmark.json / benchmark.md")
