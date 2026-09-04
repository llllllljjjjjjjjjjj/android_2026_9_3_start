#!/usr/bin/env python3
"""Attach and dump encryption keys via loadClass+reflection."""
import frida
import sys
import time
import json

HOST = '127.0.0.1:27042'
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 13343
SCRIPT = r'projects\sdxy\hooks\read_keys2.js'


def on_message(message, data):
    if message.get('type') == 'send':
        print('[msg]', message.get('payload'))
    elif message.get('type') == 'error':
        print('[err]', message.get('stack') or message.get('description'))
    else:
        print('[log]', message)


def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    print('[*] attaching pid', PID)
    session = dev.attach(PID)
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        src = f.read()
    script = session.create_script(src)
    script.on('message', on_message)
    script.load()
    time.sleep(2)
    try:
        result = script.exports_sync.dump()
        print('[RESULT]')
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    except Exception as e:
        print('[!] rpc error:', e)
    time.sleep(2)
    try:
        session.detach()
    except Exception:
        pass
    print('[*] done')


if __name__ == '__main__':
    main()
