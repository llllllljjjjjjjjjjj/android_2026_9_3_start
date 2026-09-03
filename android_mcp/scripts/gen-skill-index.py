#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gen-skill-index.py - Generate the reverse-kit-index SKILL.md FROM the skill
SKILL.md files (.dsh/skills/<name>/SKILL.md frontmatter). Every "role" cell is
the description verbatim, so the index faithfully reflects what each skill
itself declares.

Output: .dsh/skills/reverse-kit-index/SKILL.md
"""
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, ".dsh", "skills")
DST_INDEX_DIR = os.path.join(ROOT, ".dsh", "skills", "reverse-kit-index")

SKIP = {"risk-control-adversary-workspace"}

ORDER = [
    "android-recon",
    "android-unpack",
    "android-dynamic",
    "protocol-signature-reverser",
    "reverse-skill-evolver",
    "darwin-skill",
    "risk-control-adversary",
]

# Boundaries are curated from each skill's body (no structured field exists in the
# original frontmatter). Kept short; everything else comes from the originals.
BOUNDARIES = {
    "android-recon": "不做脱壳/Hook/签名还原",
    "android-unpack": "脱完交 android-recon 做静态分析",
    "android-dynamic": "不做纯算实现/签名还原（交 protocol-signature-reverser）",
    "protocol-signature-reverser": "不做运行期 Hook（交 android-dynamic）",
    "reverse-skill-evolver": "元技能，管理前 4 个逆向技能",
    "darwin-skill": "通用 skill 优化框架，不限于逆向",
    "risk-control-adversary": "只读 projects/；只写 docs/risk-control-plan.md",
}

INDEX_FRONTMATTER = """---
name: reverse-kit-index
description: Android 逆向便携工作台「技能总索引」，由原 7 份 SKILL.md 转化生成。当任务涉及逆向、或不确定该用哪个技能、或需要了解全部技能分工时加载本技能做路由；每个技能的作用直接引用其原 SKILL.md 的 description。触发词：技能总览、skill清单、技能索引、技能路由、该用哪个技能、所有技能、7个技能、哪个skill、分工。
whenToUse: 用户询问技能清单/分工、任务较模糊需要路由到专项技能、或需要了解整个逆向工作台能力时
---
"""


def parse_frontmatter(path):
    raw = open(path, encoding="utf-8").read()
    m = re.match(r"^---\r?\n(.*?)\r?\n---", raw, re.S)
    if not m:
        return None
    fm = yaml.safe_load(m.group(1))
    return fm if isinstance(fm, dict) else None


def main():
    rows = []
    for name in ORDER:
        md = os.path.join(SRC, name, "SKILL.md")
        if not os.path.exists(md):
            print(f"[gen-skill-index] WARN missing {md}", file=sys.stderr)
            continue
        fm = parse_frontmatter(md)
        if not fm or not fm.get("description"):
            print(f"[gen-skill-index] WARN no frontmatter/description in {md}", file=sys.stderr)
            continue
        desc = str(fm["description"]).replace("|", "\\|").replace("\n", " ")
        boundary = BOUNDARIES.get(name, "")
        rows.append(f"| **{name}** | {desc} | {boundary} |")

    body = INDEX_FRONTMATTER
    body += "# Reverse Kit — 技能总索引\n\n"
    body += (
        "> 本技能是路由/索引：**不执行具体逆向**，负责把任务分派到 7 个专项技能。\n"
        "> 每行「作用」**直接引用原 SKILL.md 的 description**（原样转化），触发词包含在其中。\n"
        "> 确认目标后，用 skill 工具加载对应技能。\n\n"
    )
    body += "## 技能总览（来自原 SKILL.md frontmatter）\n\n"
    body += "| 技能 | 作用（原 SKILL.md description） | 边界 |\n"
    body += "|------|----------------------------------|------|\n"
    body += "\n".join(rows) + "\n\n"

    body += """## 工作流阶段映射

```
§1 环境就绪 / §2 静态分析 / §3 抓包治理  → android-recon（+ reverse_index / frida_orchestrator）
有壳？（jadx 空壳/方法体 nop）            → android-unpack（脱完回 §2）
§4 签名逆向                              → protocol-signature-reverser（+ algo_lab / frida_rpc_call）
§5 动态调试                              → android-dynamic（+ frida_orchestrator / .venv-frida-*）
风控方案                                → risk-control-adversary
技能进化/评估/优化                       → reverse-skill-evolver / darwin-skill
```

## 配套能力速查

| 能力 | 入口 |
|------|------|
| 反编译产物索引/检索 | `mcp__reverse_index__*`（index_project/search_code/find_endpoint/find_symbol…） |
| ADB/Root/Frida 编排、frida_rpc_call、UI 自动化 | `mcp__frida_orchestrator__*`（80 工具） |
| 编码识别、Hash/HMAC 验证、python 复现器 | `mcp__algo_lab__*` |
| Charles 抓包会话 | `mcp__charles__*`（需 GUI 开 8888） |
| jadx / apktool / bundled adb | `tools\\jadx\\bin\\jadx.bat`、`tools\\apktool\\apktool.bat`、`android_mcp\\toolchain\\bin\\windows\\platform-tools\\adb.exe` |
| Frida 客户端（版本对齐） | `.venv-frida-16.5.7\\`（florida-server/f1657）、`.venv-frida-16.7.19\\`（frida-server） |

## 使用方式

1. 按上表匹配任务 → 加载对应技能（skill 工具调用技能名）。
2. 拿不准等级/策略 → 各技能内有判定矩阵（如 android-dynamic 安全等级 L0-L5、android-unpack 加固成功率表）。
3. 任务完成后 → 如需沉淀，交给 reverse-skill-evolver 评估归档。

> 总览与项目根 `AGENTS.md` 一致；各技能细节以 `.dsh/skills/<name>/SKILL.md` 为准。
"""

    os.makedirs(DST_INDEX_DIR, exist_ok=True)
    out = os.path.join(DST_INDEX_DIR, "SKILL.md")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(body)
    print(f"[gen-skill-index] generated {out} from {len(rows)} original SKILL.md files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
