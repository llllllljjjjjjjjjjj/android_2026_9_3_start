#!/usr/bin/env python3
import frida
import sys
import time
import json

HOST = '127.0.0.1:27042'
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 13343
SCRIPT = r'projects\sdxy\hooks\diag_classes.js'


def on_message(message, data):
    if message.get('type') == 'send':
        print('[msg]', message.get('payload'))
    elif message.get('type') == 'error':
        print('[err]', message.get('stack') or message.get('description'))


def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    print('[*] attaching', PID)
    session = dev.attach(PID)
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        src = f.read()
    script = session.create_script(src)
    script.on('message', on_message)
    script.load()
    time.sleep(1)
    try:
        r = script.exports_sync.diag()
        print(json.dumps(r, indent=2))
    except Exception as e:
        print('[!]', e)
    try:
        session.detach()
    except Exception:
        pass


if __name__ == '__main__':
    main()
