# -*- coding: utf-8 -*-
"""对 iteration-N 的产出做断言评分，生成 grading.json

用法: python grade.py <iteration_dir>
"""
import json, os, sys, re, glob

IT = sys.argv[1] if len(sys.argv) > 1 else \
    r"D:\reserve_agent\android\risk-control-adversary-workspace\iteration-1"

# 断言定义：(id, 描述, 检测函数)
def has_all(text, kws):
    return all(k in text for k in kws)

E0 = [
    ("A1 七层链路结构", lambda t: sum(1 for k in ["触发层","参数层","前置特征层","签名层","传输层","响应层","回执层"] if k in t) >= 6),
    ("A2 前置接口表", lambda t: "history_words_record" in t and ("前置" in t)),
    ("A3 紧邻特征上报表", lambda t: "upload_ei_feature" in t and ("紧邻" in t or "配对" in t)),
    ("A4 配对强度标注", lambda t: "配对强度" in t or ("强度" in t and "强" in t)),
    ("A5 因果验证表", lambda t: ("阻断" in t and "实验" in t) or "因果验证" in t),
    ("A6 降级分级判据", lambda t: "软降级" in t and "硬拒绝" in t),
    ("A7 缺证据标注", lambda t: ("[未知]" in t or "[未证]" in t or "未知" in t)),
    ("A8 时序≠因果纪律", lambda t: "推测" in t and ("已实证" in t or "阻断" in t)),
]
E1 = [
    ("B1 七层链路结构", lambda t: sum(1 for k in ["触发层","参数层","前置特征层","签名层","传输层","响应层","回执层"] if k in t) >= 6),
    ("B2 前置依赖识别", lambda t: "aweme/detail" in t and ("aweme_author" in t or "comment_count" in t)),
    ("B3 三列联动配对表", lambda t: "前置" in t and "紧邻" in t and "回执" in t),
    ("B4 因果分级(已实证/推测)", lambda t: "已实证" in t and "推测" in t),
    ("B5 降级分级判据", lambda t: "软降级" in t and "硬拒绝" in t),
    ("B6 不确定结论标注", lambda t: ("[未证]" in t or "[未知]" in t or "不完整" in t or "待验证" in t)),
]
E2 = [
    ("C1 正确选工作流 D", lambda t: "工作流" in t and ("D" in t) and ("七层" in t or "链路" in t)),
    ("C2 前置埋点专章", lambda t: "前置" in t and ("埋点" in t or "上报" in t) and ("配对" in t or "紧邻" in t)),
    ("C3 知识库沉淀清单", lambda t: ("E-28" in t or "E-2" in t) and ("L1" in t or "沉淀" in t)),
    ("C4 埋点实证发现", lambda t: "key" in t and "iv" in t and ("明文" in t)),
    ("C5 配对关系表", lambda t: "配对" in t and "前置" in t),
    ("C6 因果/待验证清单", lambda t: ("待验证" in t or "阻断" in t)),
]

MAP = {"search-chain-fullflow": E0, "comment-chain-fullflow": E1, "risk-points-scan": E2}


def read_dir(d):
    txt = ""
    for p in glob.glob(os.path.join(d, "**", "*"), recursive=True):
        if os.path.isfile(p) and p.lower().endswith((".md", ".txt", ".json")):
            try:
                txt += open(p, encoding="utf-8", errors="ignore").read() + "\n"
            except Exception:
                pass
    return txt


for name, asserts in MAP.items():
    for ver in ("with_skill", "old_skill"):
        d = os.path.join(IT, name, ver, "outputs")
        if not os.path.isdir(d):
            continue
        t = read_dir(d)
        results = []
        for aid, fn in asserts:
            try:
                passed = bool(fn(t))
            except Exception:
                passed = False
            results.append({"text": aid, "passed": passed,
                            "evidence": ("命中" if passed else "未命中")})
        npass = sum(1 for r in results if r["passed"])
        out = {
            "eval_name": name,
            "configuration": ver,
            "pass_rate": round(npass / len(results), 3),
            "passed": npass,
            "total": len(results),
            "expectations": results,
            "chars": len(t),
        }
        p = os.path.join(IT, name, ver, "grading.json")
        json.dump(out, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"{name:26s} {ver:11s} pass={npass}/{len(results)} rate={out['pass_rate']} chars={len(t)}")
