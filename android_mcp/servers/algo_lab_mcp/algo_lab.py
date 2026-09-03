from __future__ import annotations

import base64
import binascii
import difflib
import gzip
import hashlib
import hmac
import json
import re
import subprocess
import sys
import zlib
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit

from android_mcp.common.paths import resolve_under_root, safe_output_path, target_artifacts


HEX_RE = re.compile(r"^[0-9a-fA-F]+$")
B64_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")
B64URL_RE = re.compile(r"^[A-Za-z0-9_-]+={0,2}$")


CRYPTO_CONSTANTS = {
    "aes_sbox": bytes.fromhex("637c777bf26b6fc53001672bfed7ab76"),
    "sha256_k_prefix_be": bytes.fromhex("428a2f9871374491b5c0fbcfe9b5dba5"),
    "md5_t_prefix_le": bytes.fromhex("78a46ad756b7c7e8db702024eecebdc1"),
    "crc32_table_prefix_le": bytes.fromhex("00000000963007772c610eeeba510999"),
    "chacha20_sigma": b"expand 32-byte k",
}


def _preview_bytes(data: bytes, limit: int = 96) -> Dict[str, object]:
    text = data[:limit].decode("utf-8", errors="replace")
    return {"len": len(data), "hex_prefix": data[:limit].hex(), "utf8_prefix": text}


def detect_encoding(value: str) -> Dict[str, object]:
    raw = value.strip()
    results: List[Dict[str, object]] = []
    raw_bytes = raw.encode("utf-8", errors="replace")
    results.append({"kind": "raw_utf8", "confidence": "baseline", "decoded": _preview_bytes(raw_bytes)})

    if "%" in raw:
        decoded = unquote(raw)
        results.append({"kind": "url_percent", "confidence": "medium", "value": decoded, "decoded": _preview_bytes(decoded.encode())})

    if len(raw) % 2 == 0 and HEX_RE.match(raw):
        try:
            data = bytes.fromhex(raw)
            results.append({"kind": "hex", "confidence": "high", "decoded": _preview_bytes(data)})
            _append_compression(results, data, "hex")
        except ValueError:
            pass

    for kind, regex, altchars in [("base64", B64_RE, None), ("base64url", B64URL_RE, b"-_")]:
        if len(raw) >= 4 and regex.match(raw):
            padded = raw + "=" * ((4 - len(raw) % 4) % 4)
            try:
                data = base64.b64decode(padded.encode(), altchars=altchars, validate=False)
                if data:
                    results.append({"kind": kind, "confidence": "medium", "decoded": _preview_bytes(data)})
                    _append_compression(results, data, kind)
            except binascii.Error:
                pass

    try:
        parsed = json.loads(raw)
        results.append({"kind": "json", "confidence": "high", "type": type(parsed).__name__, "keys": list(parsed.keys())[:30] if isinstance(parsed, dict) else None})
    except Exception:
        pass

    return {"value_len": len(value), "candidates": results}


def _append_compression(results: List[Dict[str, object]], data: bytes, source_kind: str) -> None:
    for kind, func in [("gzip", gzip.decompress), ("zlib", zlib.decompress)]:
        try:
            out = func(data)
            results.append({"kind": f"{source_kind}+{kind}", "confidence": "high", "decoded": _preview_bytes(out)})
        except Exception:
            continue


def normalize_request(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: str = "",
    include_headers: Optional[List[str]] = None,
    sort_query: bool = True,
) -> Dict[str, object]:
    split = urlsplit(url)
    query_pairs = parse_qsl(split.query, keep_blank_values=True)
    if sort_query:
        query_pairs = sorted(query_pairs)
    query = urlencode(query_pairs, doseq=True)
    path = split.path or "/"
    normalized_url = f"{split.scheme}://{split.netloc}{path}"
    if query:
        normalized_url += "?" + query
    headers = headers or {}
    selected_headers: List[str] = []
    if include_headers:
        lowered = {k.lower(): v for k, v in headers.items()}
        for key in include_headers:
            if key.lower() in lowered:
                selected_headers.append(f"{key.lower()}:{lowered[key.lower()]}")
    canonical = "\n".join([method.upper(), path, query, *selected_headers, body])
    return {
        "method": method.upper(),
        "normalized_url": normalized_url,
        "path": path,
        "query": query,
        "selected_headers": selected_headers,
        "canonical": canonical,
        "canonical_hex": canonical.encode("utf-8").hex(),
    }


def diff_values(a: str, b: str, context: int = 3) -> Dict[str, object]:
    a_lines = a.splitlines() or [a]
    b_lines = b.splitlines() or [b]
    diff = list(difflib.unified_diff(a_lines, b_lines, fromfile="a", tofile="b", lineterm="", n=context))
    return {"a_len": len(a), "b_len": len(b), "equal": a == b, "diff": diff[:500]}


def diff_requests(req1: Dict[str, object], req2: Dict[str, object]) -> Dict[str, object]:
    left = json.dumps(req1, ensure_ascii=False, indent=2, sort_keys=True)
    right = json.dumps(req2, ensure_ascii=False, indent=2, sort_keys=True)
    return diff_values(left, right, context=5)


def _decode_input(value: str, encoding: str) -> bytes:
    if encoding == "utf8":
        return value.encode("utf-8")
    if encoding == "hex":
        return bytes.fromhex(value)
    if encoding == "base64":
        return base64.b64decode(value + "=" * ((4 - len(value) % 4) % 4))
    raise ValueError("encoding must be utf8, hex, or base64")


def _expected_matches(digest: bytes, expected: str) -> List[str]:
    expected_clean = expected.strip()
    encodings = {
        "hex_lower": digest.hex(),
        "hex_upper": digest.hex().upper(),
        "base64": base64.b64encode(digest).decode(),
        "base64url": base64.urlsafe_b64encode(digest).decode().rstrip("="),
    }
    return [kind for kind, value in encodings.items() if value == expected_clean]


def test_hash_candidates(input_value: str, expected: str, input_encoding: str = "utf8") -> Dict[str, object]:
    data = _decode_input(input_value, input_encoding)
    matches: List[Dict[str, object]] = []
    algorithms = ["md5", "sha1", "sha224", "sha256", "sha384", "sha512", "blake2s", "blake2b"]
    for alg in algorithms:
        digest = hashlib.new(alg, data).digest()
        matched = _expected_matches(digest, expected)
        if matched:
            matches.append({"algorithm": alg, "output_encodings": matched})
    return {"input_len": len(data), "expected_len": len(expected), "matches": matches}


def test_hmac_candidates(input_value: str, expected: str, keys: List[str], input_encoding: str = "utf8", key_encoding: str = "utf8") -> Dict[str, object]:
    data = _decode_input(input_value, input_encoding)
    matches: List[Dict[str, object]] = []
    for key in keys:
        key_bytes = _decode_input(key, key_encoding)
        for alg in ["md5", "sha1", "sha224", "sha256", "sha384", "sha512"]:
            digest = hmac.new(key_bytes, data, alg).digest()
            matched = _expected_matches(digest, expected)
            if matched:
                matches.append({"algorithm": f"hmac-{alg}", "key": key, "output_encodings": matched})
    return {"input_len": len(data), "keys_tested": len(keys), "matches": matches}


def scan_crypto_constants(path: str, recursive: bool = True, max_file_mb: int = 80) -> Dict[str, object]:
    root = resolve_under_root(path)
    if not root.exists():
        raise ValueError(f"path not found: {root}")
    files: Iterable[Path]
    if root.is_dir():
        files = (p for p in root.rglob("*") if p.is_file()) if recursive else (p for p in root.iterdir() if p.is_file())
    else:
        files = [root]
    max_bytes = max_file_mb * 1024 * 1024
    hits: List[Dict[str, object]] = []
    scanned = 0
    for file in files:
        try:
            if file.stat().st_size > max_bytes:
                continue
            data = file.read_bytes()
        except OSError:
            continue
        scanned += 1
        for name, needle in CRYPTO_CONSTANTS.items():
            idx = data.find(needle)
            if idx >= 0:
                hits.append({"file": str(file), "constant": name, "offset": idx, "hex": needle.hex()})
    return {"path": str(root), "files_scanned": scanned, "hits": hits}


def analyze_signature_samples(samples: List[str]) -> Dict[str, object]:
    charsets = []
    for value in samples:
        if HEX_RE.match(value) and len(value) % 2 == 0:
            kind = "hex"
        elif B64_RE.match(value):
            kind = "base64-ish"
        elif B64URL_RE.match(value):
            kind = "base64url-ish"
        else:
            kind = "mixed"
        charsets.append(kind)
    lengths = [len(s) for s in samples]
    unique = len(set(samples))
    return {
        "count": len(samples),
        "lengths": lengths,
        "unique_count": unique,
        "all_same": unique == 1,
        "charset_guess": charsets,
        "fixed_length": len(set(lengths)) == 1 if lengths else False,
        "notes": [
            "fixed hex length 32 often maps to MD5-like output",
            "fixed hex length 64 often maps to SHA-256-like output",
            "variable base64 often indicates binary structure or encrypted blob",
        ],
    }


def generate_python_reproducer(
    target: str,
    algorithm: str,
    output: Optional[str] = None,
    key: Optional[str] = None,
    key_encoding: str = "utf8",
) -> Dict[str, object]:
    out_path = safe_output_path(target_artifacts(target), output, f"reproducer_{algorithm.replace('-', '_')}.py")
    laohe_key_expr = "None"
    if key is not None:
        if key_encoding == "hex":
            laohe_key_expr = f"bytes.fromhex({key!r})"
        elif key_encoding == "base64":
            laohe_key_expr = f"base64.b64decode({key!r})"
        else:
            laohe_key_expr = f"{key!r}.encode('utf-8')"
    content = f'''import base64
import hashlib
import hmac


ALGORITHM = {algorithm!r}
LAOHE_KEY = {laohe_key_expr}


def sign(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    if ALGORITHM.startswith("hmac-"):
        if LAOHE_KEY is None:
            raise ValueError("HMAC reproducer requires LAOHE_KEY")
        digest_name = ALGORITHM.split("-", 1)[1]
        return hmac.new(LAOHE_KEY, data, digest_name).hexdigest()
    return hashlib.new(ALGORITHM, data).hexdigest()


if __name__ == "__main__":
    import sys
    payload = sys.argv[1] if len(sys.argv) > 1 else ""
    print(sign(payload))
'''
    out_path.write_text(content, encoding="utf-8")
    return {"path": str(out_path), "algorithm": algorithm, "key_encoding": key_encoding if key is not None else None}


def verify_reproducer(script_path: str, vectors: List[Dict[str, str]], timeout: int = 20) -> Dict[str, object]:
    script = resolve_under_root(script_path)
    if not script.exists():
        raise ValueError(f"script not found: {script}")
    results = []
    for vec in vectors:
        data = vec["input"]
        expected = vec["expected"]
        completed = subprocess.run(
            [sys.executable, str(script), data],
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        actual = completed.stdout.strip()
        results.append({"input": data, "expected": expected, "actual": actual, "ok": actual == expected, "stderr": completed.stderr})
    return {"script": str(script), "total": len(results), "passed": sum(1 for r in results if r["ok"]), "results": results}

