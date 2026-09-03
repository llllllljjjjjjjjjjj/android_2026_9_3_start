# -*- coding: utf-8 -*-
"""charles_api.py — Charles Web Interface HTTP API 封装

Charles 5.x 的 Web Interface 没有独立端口：通过代理端口（默认 8888）访问，
magic host 为 control.charles（请求必须是代理绝对 URI 形式 + Host: control.charles）。

提供：
    GET /session/export-json    导出当前会话（JSON 数组，Charles .chlsj 格式）
    GET /recording/start|stop   录制开关
    GET /recording/status       录制状态（部分版本 404，调用方有兜底）
"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
from typing import Any, Dict, List, Optional


def _auth_headers():
    user = os.environ.get("CHARLES_WEB_USER", "")
    password = os.environ.get("CHARLES_WEB_PASSWORD", "")
    if not user and not password:
        return {}
    token = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    return {"Authorization": f"Basic {token}"}


DEFAULT_PORT = 8888


class CharlesApiError(RuntimeError):
    pass


def _get(port: int, path: str, timeout: float = 60.0) -> bytes:
    """通过代理端口访问 magic host control.charles。

    必须显式建 ProxyHandler（绝对 URI 代理请求），否则 urllib 会把
    control.charles 当真实域名解析直连。
    """
    url = f"http://control.charles{path}"
    proxy = urllib.request.ProxyHandler({"http": f"http://127.0.0.1:{port}"})
    opener = urllib.request.build_opener(proxy)
    req = urllib.request.Request(url, headers={"Host": "control.charles", "Accept": "application/json", **_auth_headers()})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        raise CharlesApiError(f"HTTP {e.code} {url}（Charles Web Interface 不可用？）") from e
    except urllib.error.URLError as e:
        raise CharlesApiError(f"连接失败 {url}: {e.reason}（Charles 在跑吗？端口 {port}？）") from e


def export_session(port: int = DEFAULT_PORT, timeout: float = 120.0) -> List[Dict[str, Any]]:
    """导出当前录制会话，返回条目列表（统一成 dict 结构）。"""
    candidates = ["/session/export-json", "/session/export"]
    last_err: Optional[Exception] = None
    for path in candidates:
        try:
            raw = _get(port, path, timeout=timeout)
            text = raw.decode("utf-8", errors="replace").lstrip("﻿")
            if not text.strip():
                continue
            try:
                data = json.loads(text)
                return _normalize(data)
            except json.JSONDecodeError:
                last_err = ValueError(f"{path} 返回非 JSON（前 200 字符: {text[:200]}）")
        except CharlesApiError as e:
            last_err = e
    raise CharlesApiError(f"无法导出会话: {last_err}")


def _normalize(data: Any) -> List[Dict[str, Any]]:
    """Charles 5.x export-json 返回的是数组；旧版可能是 {entries:[...]}。统一为条目列表。"""
    if isinstance(data, list):
        return [e if isinstance(e, dict) else {"raw": e} for e in data]
    if isinstance(data, dict):
        for key in ("entries", "requests", "sessions"):
            if isinstance(data.get(key), list):
                return [e if isinstance(e, dict) else {"raw": e} for e in data[key]]
        return [data]
    return []


def recording(port: int = DEFAULT_PORT, action: str = "status") -> Dict[str, Any]:
    mapping = {"start": "/recording/start", "stop": "/recording/stop", "status": "/recording/status"}
    path = mapping.get(action)
    if not path:
        raise CharlesApiError(f"未知 action: {action}（start/stop/status）")
    try:
        raw = _get(port, path, timeout=30)
        text = raw.decode("utf-8", errors="replace").strip()
        return {"action": action, "response": text[:200]}
    except CharlesApiError:
        # 某些版本 status 端点 404；失败时兜底探测根路径
        try:
            _get(port, "/", timeout=10)
            return {"action": action, "response": "web-interface-alive", "note": "status 端点不可用，根路径可达"}
        except CharlesApiError as e:
            raise CharlesApiError(f"recording {action} 失败且根路径不可达: {e}") from e


def summarize(entry: Dict[str, Any]) -> Dict[str, Any]:
    """从 Charles .chlsj 条目里提炼 {url, method, status, headers, body} 摘要。

    .chlsj 格式：URL 拆为 scheme/host/path/query；headers 是 [{name,value},...] 列表；
    body 是 {"encoding":"base64","encoded":"..."}。旧版/HAR 风格字段也兼容。
    """
    # URL：优先拼 .chlsj 的拆分字段
    scheme = entry.get("scheme", "")
    host = entry.get("host", "")
    path = entry.get("path", "")
    query = entry.get("query", "")
    if scheme and host:
        url = f"{scheme}://{host}{path}" + (f"?{query}" if query else "")
    else:
        url = entry.get("url") or entry.get("fullURL") or ""

    method = entry.get("method") or ""

    # 响应状态码
    resp = entry.get("response")
    status = ""
    if isinstance(resp, dict):
        status = resp.get("status") or entry.get("responseStatus") or ""

    # 请求头：.chlsj 是列表，HAR 风格是 dict
    req = entry.get("request") or {}
    if not isinstance(req, dict):
        req = {}
    hdr = req.get("header", {})
    if isinstance(hdr, dict):
        hdr_list = hdr.get("headers", [])
        if isinstance(hdr_list, list):
            headers = {h.get("name", ""): h.get("value", "") for h in hdr_list if isinstance(h, dict)}
        else:
            headers = hdr
    elif isinstance(hdr, list):
        headers = {h.get("name", ""): h.get("value", "") for h in hdr if isinstance(h, dict)}
    else:
        headers = {}

    # 请求体：.chlsj 是 base64，解码时保留原文（二进制则标注）
    body = req.get("body", {})
    if isinstance(body, dict) and body.get("encoding") == "base64" and "encoded" in body:
        import base64

        try:
            raw = base64.b64decode(body["encoded"])
            body = {
                "encoding": "base64",
                "decoded_text": raw.decode("utf-8", errors="replace"),
                "is_binary": "�" in raw.decode("utf-8", errors="replace"),
                "size": len(raw),
            }
        except Exception:
            body = {"encoding": "base64", "encoded_preview": str(body.get("encoded"))[:200]}

    return {"url": url, "method": method, "status": status, "headers": headers, "body": body}


def find_entries(port: int = DEFAULT_PORT, pattern: str = "", method: str = "", limit: int = 20) -> List[Dict[str, Any]]:
    """导出会话并按 URL 子串/正则过滤。pattern 为空时返回最近全部。"""
    import re

    entries = export_session(port)
    rx = re.compile(pattern) if pattern else None
    out: List[Dict[str, Any]] = []
    for e in entries:
        s = summarize(e)
        if method and s["method"].upper() != method.upper():
            continue
        if rx and not rx.search(s["url"]):
            continue
        out.append(s)
        if len(out) >= limit:
            break
    return out


def save_session(port: int = DEFAULT_PORT, dest: str = "") -> Dict[str, Any]:
    """把当前会话导出并落盘（默认 projects/dy/capture/charles_session.json）。"""
    entries = export_session(port)
    if not dest:
        dest = "capture/charles_session.json"
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    return {"saved": dest, "entries": len(entries), "ts": time.strftime("%Y-%m-%d %H:%M:%S")}
