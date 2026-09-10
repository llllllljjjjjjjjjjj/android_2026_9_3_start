# -*- coding: utf-8 -*-
"""抖音 TTNet cronet TLS 明文抓包 runner（hook libttboringssl 的 SSL_read/SSL_write）。
依赖: frida (venv 16.5.7), 设备 florida-server 16.5.9 已运行。
用法:
  spawn 模式(推荐, 冷启抓全量):  python run_capture.py -f -o out.log
  attach 模式(已有进程):         python run_capture.py -p 包名 -o out.log
输出: 明文 printable 内容写 <out>; 请求头含 x-tt-token/x-argus 时单独标注。
"""
import argparse, sys, time, frida

PKG = "com.ss.android.ugc.aweme"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-f", "--spawn", action="store_true", help="spawn 冷启抖音")
    ap.add_argument("-p", "--pid", type=int, default=0, help="attach 到已运行进程 pid")
    ap.add_argument("-o", "--out", default="dy_tls_plain.txt")
    ap.add_argument("-H", "--host", default="127.0.0.1:27042")
    args = ap.parse_args()

    dev = frida.get_device_manager().add_remote_device(args.host)
    if args.spawn:
        pid = dev.spawn([PKG])
        session = dev.attach(pid)
        dev.resume(pid)
        print(f"[*] spawned {PKG} pid={pid}")
    elif args.pid:
        pid = args.pid
        session = dev.attach(pid)
        print(f"[*] attached pid={pid}")
    else:
        # 尝试 attach 到包名 (frida 支持按进程名 attach)
        session = dev.attach(PKG)
        print(f"[*] attached {PKG}")

    js = open("script.js", "r", encoding="utf-8").read()
    script = session.create_script(js)

    fh = open(args.out, "wb")
    interesting = (b"x-tt-token", b"x-argus", b"X-Argus", b"X-Ladon",
                   b"install_id", b"device_id", b"tz_name", b"app_name")

    def printable(data):
        # 保留可打印 ASCII + 换行/回车/tab
        return bytes(b if (0x20 <= b < 0x7f) or b in (9, 10, 13) else ord(".") for b in data)

    def on_message(msg, data):
        if msg.get("type") == "error":
            print("[error]", msg, file=sys.stderr)
            return
        if not data:
            # 状态消息(如 function 名 / stack)
            pl = msg.get("payload", {})
            fn = pl.get("function")
            if fn:
                print(f"[event] {fn}")
            return
        fn = msg["payload"].get("function", "?")
        fh.write(b"\n===== [" + fn.encode() + b"] =====\n")
        p = printable(data)
        fh.write(p + b"\n")
        fh.flush()
        low = data.lower()
        if any(t in low for t in interesting):
            print(f"[!] {fn} hit interesting header/token")
            # 打印含关键头的行
            for line in p.split(b"\n"):
                if any(t in line.lower() for t in interesting):
                    print("    " + line.decode("latin-1"))

    script.on("message", on_message)
    script.load()
    print("[*] script loaded, capturing... kill process to stop", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    fh.close()
    session.detach()
    print("[*] done ->", args.out)

if __name__ == "__main__":
    main()
