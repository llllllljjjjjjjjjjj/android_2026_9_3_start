# -*- coding: utf-8 -*-
"""风控健康检查公共模块（依据 docs/flow-and-risk.md）

三个能力：
  1. 埋点配对校验 —— 业务请求是否都有紧邻的特征上报（upload_ei_feature / app_log）
  2. 降级检测 —— 区分"真数据" / "软降级(空壳)" / "硬拒绝(-99999)"
  3. 会话凭证追踪 —— search_id / authentication_token 的签发与回带
"""
import re
import time

# 业务请求路径特征
BIZ_PATHS = {
    "search": ["/aweme/v2/search/general/stream/", "/aweme/v1/general/search/stream/"],
    "comment": ["/aweme/v2/comment/list/stream/", "/aweme/v1/comment/list/"],
    "detail": ["/aweme/v1/aweme/detail/", "/aweme/v1/multi/aweme/detail/"],
}
# 埋点/特征上报路径特征（前置配对要求）
TELEMETRY_PATHS = [
    "/aweme/v1/search/memory/upload_ei_feature/",
    "/service/2/app_log/",
    "/aweme/v1/aweme/stats/",
    "/monitor/collect/",
    "/service/2/app_log/performance/",
]


def classify_path(path):
    """返回 ('biz', kind) / ('telemetry', None) / ('other', None)"""
    if not path:
        return "other", None
    p = path.split("?")[0]
    for kind, pats in BIZ_PATHS.items():
        for pat in pats:
            if p.startswith(pat.rstrip("/")) or pat.rstrip("/") in p:
                return "biz", kind
    for t in TELEMETRY_PATHS:
        if t.rstrip("/") in p:
            return "telemetry", None
    return "other", None


class RiskHealth:
    """记录一次采集会话的风控健康度"""

    def __init__(self, link):
        self.link = link
        self.events = []          # [(ts, kind, path)]
        self.biz_calls = 0
        self.telemetry_calls = 0
        self.session_ids = []     # 服务端签发的 search_id
        self.auth_tokens = []     # authentication_token

    def note(self, path):
        kind, sub = classify_path(path)
        self.events.append((time.time(), kind, path))
        if kind == "biz":
            self.biz_calls += 1
        elif kind == "telemetry":
            self.telemetry_calls += 1
        # 会话凭证抽取
        if path:
            m = re.search(r"search_id=([0-9A-F]{22,})", path)
            if m:
                self.session_ids.append(m.group(1))
            m2 = re.search(r"authentication_token=([A-Za-z0-9_\-]+)", path)
            if m2:
                self.auth_tokens.append(m2.group(1))

    def pairing_health(self):
        """埋点配对：每个业务请求附近（±8s / ±3 事件）是否有埋点上报"""
        biz = [i for i, (_, k, _) in enumerate(self.events) if k == "biz"]
        tel = [i for i, (_, k, _) in enumerate(self.events) if k == "telemetry"]
        if not biz:
            return {"ok": False, "reason": "no biz call", "paired": 0, "total": 0}
        paired = 0
        for bi in biz:
            if any(abs(bi - ti) <= 3 for ti in tel):
                paired += 1
        return {"ok": paired > 0, "paired": paired, "total": len(biz),
                "ratio": round(paired / len(biz), 2)}

    def report(self):
        ph = self.pairing_health()
        lines = [
            f"[风控健康] 链路={self.link}",
            f"  业务请求: {self.biz_calls}  埋点上报: {self.telemetry_calls}",
            f"  埋点配对: {ph['paired']}/{ph['total']} (ratio={ph.get('ratio')})",
        ]
        if not ph["ok"] and self.biz_calls:
            lines.append("  ⚠️ 未观测到埋点配对 —— 存在埋点缺失风险")
        if self.session_ids:
            lines.append(f"  search_id 签发: {len(self.session_ids)} 个，最新={self.session_ids[-1]}")
        if self.auth_tokens:
            lines.append(f"  auth_token: {len(self.auth_tokens)} 个")
        return "\n".join(lines)


def judge_response(body_text):
    """降级判官（依据 flow-and-risk.md §8 降级分级）

    返回 (verdict, detail)
      ok        —— 真实业务数据
      soft      —— 软降级（空壳 JSON）
      hard      —— 硬拒绝（风控码）
      unknown   —— 无法判定
    """
    if body_text is None:
        return "unknown", "no body"
    t = body_text if isinstance(body_text, str) else body_text.decode("utf-8", "ignore")

    # 硬拒绝
    for code in ("-99999", "-9998", "-9997"):
        if f'"status_code":{code}' in t.replace(" ", "") or f"status_code:{code}" in t:
            return "hard", f"风控码 {code}"

    # 软降级特征（搜索）
    if '"has_more":0' in t.replace(" ", "") and ('"category_list":[]' in t.replace(" ", "")
                                                 or '"comments":[]' in t.replace(" ", "")):
        return "soft", "空壳响应"

    # 真实数据
    if re.search(r'"(cid|aweme_id|aweme_list|desc|search_id)"\s*:', t):
        return "ok", "含业务字段"

    return "unknown", "无特征"


def print_verdict(verdict, detail, n_items=None):
    icon = {"ok": "✅", "soft": "⚠️", "hard": "❌", "unknown": "❓"}.get(verdict, "?")
    extra = f" 条目={n_items}" if n_items is not None else ""
    print(f"[判官] {icon} {verdict.upper()} — {detail}{extra}")
    if verdict == "soft":
        print("       说明: 服务端降级为空壳，非成功（AGENTS.md 禁词纪律）")
    if verdict == "hard":
        print("       说明: 风控明确拒绝，请检查埋点配对/会话凭证/节奏")
    return verdict == "ok"
