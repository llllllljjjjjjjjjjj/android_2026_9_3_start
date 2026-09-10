# -*- coding: utf-8 -*-
"""对照实验 B: HTTP/2 直发搜索（排除协议层因素；TLS 仍为 OpenSSL）
复用 search_pure 的全部纯算构造逻辑，仅传输层换 h2
"""
import sys, time, socket, ssl, json, h2.connection, h2.config
import urllib.parse
sys.path.insert(0, r"D:\reserve_agent\android\projects\dy\scripts")
import search_pure as sp

HOST = "search3-search.amemv.com"
KW = sys.argv[1] if len(sys.argv) > 1 else "太阳"


def main():
    samples = sp.load_header_samples()
    sample = samples[0]
    query_sample = sp.pick_query_sample(samples)
    bodies = sp.extract_bodies()
    tmpl = bodies[sp.SEARCH_PATH]
    tpl_params = dict(urllib.parse.parse_qsl(tmpl, keep_blank_values=True))
    keep_features = len(tpl_params.get("search_rerank_info", "")) > 100

    now_s = int(time.time())
    now_ms = int(time.time() * 1000)
    prev_ts = now_ms - 60000
    body = sp.build_search_body(tmpl, KW, 10, 0, prev_ts, None, keep_features)
    stub = sp.compute_stub(body.encode("utf-8"))
    hdrs = sp.build_headers(sample, now_s, now_ms, HOST, stub)
    qs = sp.build_public_query(query_sample, now_s, now_ms)
    path = f"/aweme/v2/search/general/stream/?{qs}"
    print(f"[*] HTTP/2 POST {HOST}{path.split('?')[0]} | body {len(body)}B")

    ctx = ssl.create_default_context()
    ctx.set_alpn_protocols(["h2"])
    sock = socket.create_connection((HOST, 443), timeout=15)
    ssock = ctx.wrap_socket(sock, server_hostname=HOST)
    print("[*] ALPN:", ssock.selected_alpn_protocol())

    cfg = h2.config.H2Configuration(client_side=True, header_encoding="utf-8")
    conn = h2.connection.H2Connection(config=cfg)
    conn.initiate_connection()
    ssock.sendall(conn.data_to_send())

    hdrs_list = [(":method", "POST"), (":scheme", "https"), (":authority", HOST), (":path", path)]
    for k, v in hdrs.items():
        if k.lower() == "host":
            continue
        hdrs_list.append((k, v))
    stream_id = conn.get_next_available_stream_id()
    conn.send_headers(stream_id, hdrs_list)
    conn.send_data(stream_id, body.encode("utf-8"), end_stream=True)
    ssock.sendall(conn.data_to_send())

    # 读响应
    resp = b""
    headers_done = False
    content_encoding = None
    while True:
        data = ssock.recv(65536)
        if not data:
            break
        for event in conn.receive_data(data):
            if isinstance(event, h2.events.ResponseReceived):
                print("[*] 响应状态:", event.headers[0][1])
                for n, v in event.headers:
                    n = n.decode() if isinstance(n, bytes) else n
                    if n in ("content-encoding", "content-length", "content-type"):
                        print("    ", n, ":", v)
            elif isinstance(event, h2.events.DataReceived):
                resp += event.data
                conn.acknowledge_received_data(event.flow_controlled_length, event.stream_id)
            elif isinstance(event, h2.events.StreamEnded):
                headers_done = True
        if headers_done:
            break
    ssock.close()
    print("[*] 响应体:", len(resp), "B")
    if not resp:
        print("[!] 空响应")
        return 2

    ok, verdict, texts, data = sp.parse_response(resp)
    print("[*] 判官:", verdict)
    for t in texts[:2]:
        print("[*] 响应块:", t[:200])
    items = sp.extract_items(data) if data else []
    print("[*] 条目:", len(items))
    if items:
        for it in items[:3]:
            print("    aid=%s desc=%s" % (it.get("aweme_id"), str(it.get("desc"))[:40]))
    json.dump({"kw": KW, "verdict": verdict, "ok": ok, "items": items,
               "raw_head": resp[:500].decode("utf-8", "ignore")},
              open(r"D:\reserve_agent\android\projects\dy\capture\pure_h2_result.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("[*] 已保存 -> capture/pure_h2_result.json")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
