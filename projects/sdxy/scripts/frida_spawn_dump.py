#!/usr/bin/env python3
"""Spawn app + inject dex_dump.js + resume + collect output."""
import frida
import sys
import time

HOST = '127.0.0.1:27042'
PKG = 'com.huachenjie.shandong_school'
SCRIPT = r'projects\sdxy\hooks\dex_dump.js'

def on_message(message, data):
    if message.get('type') == 'send':
        print('[msg]', message.get('payload'))
    elif message.get('type') == 'error':
        print('[err]', message.get('stack') or message.get('description'))
    else:
        print('[log]', message)

def main():
    dev = frida.get_device_manager().add_remote_device(HOST)
    print('[*] spawning', PKG)
    pid = dev.spawn([PKG])
    print('[*] pid', pid)
    session = dev.attach(pid)
    with open(SCRIPT, 'r', encoding='utf-8') as f:
        src = f.read()
    script = session.create_script(src)
    script.on('message', on_message)
    script.load()
    print('[*] resumed')
    dev.resume(pid)
    # wait for setTimeout(10s) + scan
    time.sleep(30)
    print('[*] done, detaching')
    session.detach()
    sys.exit(0)

if __name__ == '__main__':
    main()
