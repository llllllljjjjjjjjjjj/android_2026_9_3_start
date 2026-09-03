# -*- coding: utf-8 -*-
# paging_probe.py — 隔离实验：定位构造翻页请求 -99999 的触发因素
# A: URL改cursor=440 + body追加1假cid + 随机新stub
# B: URL改cursor=440（ts/l1不动） + body原样 + stub原样
# C: URL原样(420) + body追加1假cid + stub原样
# D: 完全原样 420（对照组，应成功）
import base64
import json
import re
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, 'android_mcp/servers/charles_mcp')
from charles_api import export_session
import requests
import zstandard as zstd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import comment_replay as cr


def oracle_sign(url, stub):
    out = cr._script.exports_sync.oracle(url, cr.BASE_HDR + '\r\nx-ss-stub\r\n' + stub)
    parts = out.split('\r\n')
    return {parts[i]: parts[i + 1] for i in range(0, len(parts) - 1, 2)}


def post(url, hdrs, body, stub=None):
    h = dict(hdrs)
    if stub is not None:
        h['x-ss-stub'] = stub
    for k in list(h):
        if k.lower() in ('x-argus', 'x-gorgon', 'x-helios', 'x-khronos', 'x-ladon', 'x-medusa'):
            del h[k]
    h.update(oracle_sign(url, h.get('x-ss-stub', '')))
    h['x-ss-req-ticket'] = str(int(time.time() * 1000))
    h['activity_now_client'] = str(int(time.time() * 1000))
    h['accept-encoding'] = 'gzip, deflate, br'
    h.pop('ttzip-version', None)
    r = requests.post(url, headers=h, data=body, timeout=30)
    raw = r.content
    s = raw.find(b'{')
    if s > 0:
        raw = raw[s:]
    j = json.JSONDecoder().raw_decode(raw.decode('utf-8', errors='replace'))[0]
    return j.get('status_code'), len(j.get('comments') or []), j.get('cursor')


def main():
    entries = export_session()
    hits = [e for e in entries if (e.get('path') or '') == '/aweme/v2/comment/list/']
    hit = max(hits, key=lambda e: e.get('times', {}).get('start', ''))
    url0 = f"https://{hit['host']}{hit['path']}?{hit['query']}"
    hdrs0 = {h['name']: h['value'] for h in hit['request']['header']['headers'] if not h['name'].startswith(':')}
    body0 = base64.b64decode(hit['request']['body']['encoded'])
    if cr._script is None:
        cr.oracle_connect()

    d = zstd.ZstdDecompressor()
    c = zstd.ZstdCompressor()
    form = d.decompress(body0).decode()
    fake_cid = '7653473964450727410'   # 假 cid（隔离"内容"因素，测试仅数量/结构影响）
    all_cids = re.search(r'session_show_cids=([^&]*)', form).group(1).split('%2C') + [fake_cid]
    form_plus = re.sub(r'(session_show_cids=)[^&]*', r'\1' + '%2C'.join(all_cids), form)
    body_plus = c.compress(form_plus.encode())
    url_cur = re.sub(r'(?<=cursor=)\d+', '440', url0)

    print('实验 A: URL改cursor=440 + body追加1假cid + 随机新stub')
    print('   ->', post(url_cur, hdrs0, body_plus, stub=secrets.token_hex(16).upper()))
    print('实验 B: URL改cursor=440（ts/l1不动） + body原样 + stub原样')
    print('   ->', post(url_cur, hdrs0, body0))
    print('实验 C: URL原样(420) + body追加1假cid + stub原样')
    print('   ->', post(url0, hdrs0, body_plus))
    print('实验 D: 完全原样 420（对照组，应成功）')
    print('   ->', post(url0, hdrs0, body0))


if __name__ == '__main__':
    main()
