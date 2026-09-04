#!/usr/bin/env python3
import frida
import sys
import time
import json

HOST = '127.0.0.1:27042'
PID = int(sys.argv[1]) if len(sys.argv) > 1 else None
SCRIPT = r'projects\sdxy\hooks\read_token.js'


def on_message(message, data):
    if message.get('type') == 'send':
        print('[msg]', message.get('payload'))
    elif message.get('type') == 'error':
        print('[err]', message.get('stack') or message.get('description'))


def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    if PID is None:
        # 自动找主进程
        for p in dev.enumerate_processes():
            if p.name == 'com.huachenjie.shandong_school' and ':' not in p.name:
                pid = p.pid
                break
        else:
            print('[!] app not running')
            return
    else:
        pid = PID
    print('[*] attaching', pid)
    session = dev.attach(pid)
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        src = f.read()
    script = session.create_script(src)
    script.on('message', on_message)
    script.load()
    time.sleep(1)
    try:
        r = script.exports_sync.dump()
        print('[RESULT]')
        print(json.dumps(r, ensure_ascii=False, indent=2, default=str))
    except Exception as e:
        print('[!]', e)
    try:
        session.detach()
    except Exception:
        pass


if __name__ == '__main__':
    main()
