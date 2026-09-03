# -*- coding: utf-8 -*-
# paging_probe2.py — body 修改触发 -99999 的根因定位（全用落盘 420 模板，不依赖 Charles API）
# E1: body 原样（对照组）
# E2: zstd 解压→重新压缩（语义不变，字节流变）
# E3: body 追加 1 个假 cid（语义变）
# E4: body 追加 1 个真实 cid（从 E1 响应拿）
import base64
import json
import re
import socket
import sys
import time
from pathlib import Path

# 强制 IPv4（防 DNS 解析到 IPv6 挂起）
_orig_gai = socket.getaddrinfo
def gai_v4(host, *a, **k):
    return [x for x in _orig_gai(host, *a, **k) if x[0] == socket.AF_INET] or _orig_gai(host, *a, **k)
socket.getaddrinfo = gai_v4

import requests
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import comment_replay as cr


def oracle_sign(url, stub):
    out = cr._script.exports_sync.oracle(url, cr.BASE_HDR + '\r\nx-ss-stub\r\n' + stub)
    parts = out.split('\r\n')
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


def post(url, hdrs, body):
    h = dict(hdrs)
    for k in list(h):
        if k.lower() in ('x-argus', 'x-gorgon', 'x-helios', 'x-khronos', 'x-ladon', 'x-medusa'):
            del h[k]
    h.update(oracle_sign(url, h.get('x-ss-stub', '')))
    h['x-ss-req-ticket'] = str(int(time.time() * 1000))
    h['activity_now_client'] = str(int(time.time() * 1000))
    h['accept-encoding'] = 'gzip, deflate, br'
    h.pop('ttzip-version', None)
    r = requests.post(url, headers=h, data=body, timeout=25)
    raw = r.content
    s = raw.find(b'{')
    if s > 0:
        raw = raw[s:]
    j = json.JSONDecoder().raw_decode(raw.decode('utf-8', errors='replace'))[0]
    return j.get('status_code'), len(j.get('comments') or []), j.get('cursor')


def main():
    hit = json.loads((ROOT / 'capture' / 'comment_paging_raw.json').read_text(encoding='utf-8'))
    url = f"https://{hit['host']}{hit['path']}?{hit['query']}"
    hdrs = {h['name']: h['value'] for h in hit['request']['header']['headers'] if not h['name'].startswith(':')}
    body = base64.b64decode(hit['request']['body']['encoded'])
    if cr._script is None:
        cr.oracle_connect()

    d = zstd.ZstdDecompressor()
    c = zstd.ZstdCompressor()
    form = d.decompress(body).decode()

    print('E1: body 原样', flush=True)
    st, n, cur = post(url, hdrs, body)
    print('   -> status=%s comments=%d cursor=%s' % (st, n, cur), flush=True)
    real_cid = None
    if st == 0 and n:
        # 从响应拿真实 cid 需要重新 post；简化：这里拿不到响应对象，E4 里单独请求
        pass

    print('E2: zstd 重压缩（语义不变，字节变）', flush=True)
    body2 = c.compress(form.encode())
    print('   字节流变化: %d -> %d bytes' % (len(body), len(body2)), flush=True)
    st, n, cur = post(url, hdrs, body2)
    print('   -> status=%s comments=%d cursor=%s' % (st, n, cur), flush=True)

    print('E3: body 追加 1 假 cid（=aweme_id）', flush=True)
    m = re.search(r'session_show_cids=([^&]*)', form)
    form3 = form.replace('session_show_cids=' + m.group(1),
                         'session_show_cids=' + m.group(1) + '%2C7653473964450727410')
    body3 = c.compress(form3.encode())
    st, n, cur = post(url, hdrs, body3)
    print('   -> status=%s comments=%d cursor=%s' % (st, n, cur), flush=True)


if __name__ == '__main__':
    main()
