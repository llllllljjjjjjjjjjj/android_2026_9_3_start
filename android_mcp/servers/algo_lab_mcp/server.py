from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from android_mcp.common.mcp_stdio import StdioMcpServer, array_prop, bool_prop, int_prop, object_schema, string_prop
from android_mcp.servers.algo_lab_mcp import algo_lab


server = StdioMcpServer("algo-lab-mcp", "0.1.0")


@server.tool("detect_encoding", "Detect common encodings/compressions for a value.", object_schema({"value": string_prop("Value to inspect.")}, required=["value"]))
def detect_encoding(value: str):
    return algo_lab.detect_encoding(value)


@server.tool(
    "normalize_request",
    "Build a canonical string from method/url/headers/body for signature experiments.",
    object_schema(
        {
            "method": string_prop("HTTP method."),
            "url": string_prop("Full URL."),
            "headers": {"type": "object", "description": "Headers object.", "additionalProperties": {"type": "string"}},
            "body": string_prop("Request body string.", ""),
            "include_headers": array_prop("Header names to include in canonical string.", {"type": "string"}),
            "sort_query": bool_prop("Sort query parameters.", True),
        },
        required=["method", "url"],
    ),
)
def normalize_request(method: str, url: str, headers: dict | None = None, body: str = "", include_headers: list | None = None, sort_query: bool = True):
    return algo_lab.normalize_request(method, url, headers, body, include_headers, sort_query)


@server.tool("diff_values", "Unified diff for two strings.", object_schema({"a": string_prop("Left value."), "b": string_prop("Right value."), "context": int_prop("Diff context.", 3, 0, 20)}, required=["a", "b"]))
def diff_values(a: str, b: str, context: int = 3):
    return algo_lab.diff_values(a, b, context)


@server.tool(
    "diff_requests",
    "Diff two request-like JSON objects.",
    object_schema({"req1": {"type": "object", "description": "Left request."}, "req2": {"type": "object", "description": "Right request."}}, required=["req1", "req2"]),
)
def diff_requests(req1: dict, req2: dict):
    return algo_lab.diff_requests(req1, req2)


@server.tool(
    "test_hash_candidates",
    "Test common hash algorithms against input/expected output.",
    object_schema(
        {
            "input_value": string_prop("Input value."),
            "expected": string_prop("Expected digest in hex/base64/base64url."),
            "input_encoding": string_prop("utf8, hex, or base64.", "utf8"),
        },
        required=["input_value", "expected"],
    ),
)
def test_hash_candidates(input_value: str, expected: str, input_encoding: str = "utf8"):
    return algo_lab.test_hash_candidates(input_value, expected, input_encoding)


@server.tool(
    "test_hmac_candidates",
    "Test common HMAC algorithms with candidate keys.",
    object_schema(
        {
            "input_value": string_prop("Input value."),
            "expected": string_prop("Expected digest in hex/base64/base64url."),
            "keys": array_prop("Candidate keys.", {"type": "string"}),
            "input_encoding": string_prop("utf8, hex, or base64.", "utf8"),
            "key_encoding": string_prop("utf8, hex, or base64.", "utf8"),
        },
        required=["input_value", "expected", "keys"],
    ),
)
def test_hmac_candidates(input_value: str, expected: str, keys: list, input_encoding: str = "utf8", key_encoding: str = "utf8"):
    return algo_lab.test_hmac_candidates(input_value, expected, keys, input_encoding, key_encoding)


@server.tool(
    "scan_crypto_constants",
    "Scan files or directories for common crypto constants.",
    object_schema(
        {
            "path": string_prop("File/dir path absolute or relative to project root."),
            "recursive": bool_prop("Recurse into directories.", True),
            "max_file_mb": int_prop("Skip files larger than this MB.", 80, 1, 1024),
        },
        required=["path"],
    ),
)
def scan_crypto_constants(path: str, recursive: bool = True, max_file_mb: int = 80):
    return algo_lab.scan_crypto_constants(path, recursive, max_file_mb)


@server.tool(
    "analyze_signature_samples",
    "Summarize signature sample lengths and charset hints.",
    object_schema({"samples": array_prop("Signature samples.", {"type": "string"})}, required=["samples"]),
)
def analyze_signature_samples(samples: list):
    return algo_lab.analyze_signature_samples(samples)


@server.tool(
    "generate_python_reproducer",
    "Generate a simple Python hash/HMAC reproducer under projects/<target>/artifacts/.",
    object_schema(
        {
            "target": string_prop("Target directory under projects/."),
            "algorithm": string_prop("hashlib algorithm or hmac-sha256 style."),
            "output": string_prop("Optional output filename under artifacts/."),
            "key": string_prop("Optional HMAC key."),
            "key_encoding": string_prop("utf8, hex, or base64.", "utf8"),
        },
        required=["target", "algorithm"],
    ),
)
def generate_python_reproducer(target: str, algorithm: str, output: str | None = None, key: str | None = None, key_encoding: str = "utf8"):
    return algo_lab.generate_python_reproducer(target, algorithm, output, key, key_encoding)


@server.tool(
    "verify_reproducer",
    "Run a generated reproducer script against input/expected vectors.",
    object_schema(
        {
            "script_path": string_prop("Script path absolute or relative to project root."),
            "vectors": array_prop("Vectors: {input, expected}.", {"type": "object"}),
            "timeout": int_prop("Timeout seconds per vector.", 20, 1, 120),
        },
        required=["script_path", "vectors"],
    ),
)
def verify_reproducer(script_path: str, vectors: list, timeout: int = 20):
    return algo_lab.verify_reproducer(script_path, vectors, timeout)


if __name__ == "__main__":
    server.run()

