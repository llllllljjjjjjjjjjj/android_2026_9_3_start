# -*- coding: utf-8 -*-
"""补齐 eval_metadata.json（viewer 需要 prompt / eval_id）"""
import json, os

IT = r"D:\reserve_agent\android\risk-control-adversary-workspace\iteration-1"
EVALS = json.load(open(r"D:\reserve_agent\android\risk-control-adversary-workspace\evals\evals.json",
                      encoding="utf-8"))

# 断言（从 grading.json 读回，注入 metadata）
for ev in EVALS["evals"]:
    name = ev["eval_name"]
    for ver in ("with_skill", "old_skill"):
        d = os.path.join(IT, name, ver)
        if not os.path.isdir(d):
            continue
        gp = os.path.join(d, "grading.json")
        asserts = []
        if os.path.exists(gp):
            g = json.load(open(gp, encoding="utf-8"))
            asserts = [{"text": e["text"], "passed": e["passed"]} for e in g.get("expectations", [])]
        meta = {
            "eval_id": ev["eval_id"],
            "eval_name": name,
            "prompt": ev["prompt"],
            "configuration": ver,
            "assertions": asserts,
        }
        json.dump(meta, open(os.path.join(d, "eval_metadata.json"), "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"  wrote {name}/{ver}/eval_metadata.json ({len(asserts)} assertions)")
print("done")
