"""Ctrip x-payload-source 在线签名 oracle 客户端（策略 E）

用法：
  1. 确保真机 frida-server 运行、adb forward 建立
  2. 运行本脚本（会自动 start-server + forward + attach）
  3. 调用 sign(md5_hex) 拿 x-payload-source

示例：
  python sign_oracle.py --md5 03041512b7ae9d31d362cf4566ba4396
"""
import os, sys, time, hashlib, frida

PKG = "ctrip.android.view"
SCRIPT = r"D:\reserve_agent\ish-portable-kit\projects\ctrip\hooks\sign_rpc.js"
ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

def ensure_frida():
    os.system(f'"{ADB}" start-server >nul 2>&1')
    os.system(f'"{ADB}" forward tcp:27042 tcp:27042 >nul 2>&1')
    time.sleep(1)

def attach():
    device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    pid = None
    try:
        for p in device.enumerate_processes():
            if p.name == PKG:
                pid = p.pid
                break
    except Exception:
        pass
    if pid is None:
        # 按 identifier 找 pid（魔改 server 进程名可能乱码）
        try:
            for a in device.enumerate_applications():
                if a.identifier == PKG:
                    pid = a.pid
                    break
        except Exception:
            pass
    if pid is None:
        # SF-016: 用 adb pidof 回退（输出落盘避免 pipe EPERM）
        tmp = os.path.join(os.environ.get("TEMP", "."), "ctrip_pid.txt")
        os.system(f'"{ADB}" shell pidof {PKG} > "{tmp}" 2>nul')
        try:
            pid = int(open(tmp, encoding="utf-8").read().strip().split()[0])
        except Exception:
            pid = None
    print("[*] pid =", pid, flush=True)
    session = device.attach(pid) if pid else device.attach(PKG)
    return device, session

def main():
    ensure_frida()
    device = frida.get_device_manager().add_remote_device("127.0.0.1:27042")
    # spawn 冷启动注入（attach 热注入会触发 libscmain.so 反检测）
    pid = device.spawn([PKG])
    session = device.attach(pid)
    code = open(SCRIPT, encoding="utf-8").read()
    script = session.create_script(code)
    def on_msg(m, d):
        if m.get("type") == "send":
            print("[js]", m.get("payload"), flush=True)
        elif m.get("type") == "error":
            print("[js-err]", m.get("stack"), flush=True)
    script.on("message", on_msg)
    script.load()
    device.resume(pid)
    time.sleep(3)

    # 演示：对给定 md5 签名
    md5hex = sys.argv[sys.argv.index("--md5") + 1] if "--md5" in sys.argv else "03041512b7ae9d31d362cf4566ba4396"
    if len(md5hex) == 32:
        print("[+] sign(", md5hex, ") =", script.exports_sync.sign(md5hex), flush=True)
        print("[+] token     =", script.exports_sync.get_token(), flush=True)
        print("[+] token2    =", script.exports_sync.get_token2(), flush=True)
        print("[+] labelV2   =", script.exports_sync.get_label_v2(), flush=True)
        print("[+] boottime  =", script.exports_sync.get_app_boot_time(), flush=True)
    else:
        print("[!] md5 must be 32 hex chars", flush=True)

    if "--serve" in sys.argv:
        print("[*] serving (Ctrl+C to stop)...", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass

if __name__ == "__main__":
    main()
