#!/usr/bin/env python3
"""Attach and scan memory for plaintext DEX, dump to device."""
import frida
import sys
import time

HOST = '127.0.0.1:27042'
PID = int(sys.argv[1]) if len(sys.argv) > 1 else 31480
SCRIPT = r'projects\sdxy\hooks\dex_scan_attach.js'


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
    time.sleep(60)
    try:
        session.detach()
    except Exception:
        pass
    print('[*] done')


if __name__ == '__main__':
    main()
