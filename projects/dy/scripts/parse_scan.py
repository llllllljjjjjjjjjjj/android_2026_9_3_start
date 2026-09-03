import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
path = sys.argv[1]
d = json.load(open(path, encoding='utf-8'))
print('file:', d['file'])
print('jni_onload:', d.get('jni_onload'))
print('strings found:', len(d['strings']))
for k, v in d['strings'].items():
    print(' ', k, v['text'][:60], 'xrefs:', len(v['xrefs']))
    for x in v['xrefs'][:8]:
        print('    from', x['from'], 'func', x['func'], 'end', x['func_end'])
print('register_natives entries:', len(d['register_natives']))
for r in d['register_natives']:
    print(' ldr:', r['ldr_ea'], 'blr:', r['blr_ea'], 'methods:', r['methods_ptr'], 'count:', r['count'])
    for t in r.get('table', [])[:40]:
        print('   ', t)
