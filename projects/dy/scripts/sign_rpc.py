# -*- coding: utf-8 -*-
"""dy 签名 RPC oracle 调用器（止损型交付：依赖真机 + 运行中 App）
用法:
  python sign_rpc.py state            # 查看实例捕获状态
  python sign_rpc.py ckheaders        # ClientKeyManager.getClientKeyHeaders() -> x-tt-token 头
  python sign_rpc.py framesign <scene> <mode>   # 八神 frameSign
  python sign_rpc.py mstoken
依赖: .venv-frida-16.5.7 (frida 16.5.7) + 设备 florida-server 16.5.9 + adb forward tcp:27042
"""
import sys, json, time, subprocess
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\sign_oracle.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"


def adb_pid():
    """SF-016: dy 级 App 反枚举，用 adb pidof 直连取 pid"""
    try:
        out = subprocess.run([ADB, "-s", SERIAL, "shell", "pidof", PKG],
                             capture_output=True, text=True, timeout=20)
        s = (out.stdout or "").strip().split()
        return int(s[0]) if s else None
    except Exception as e:
        print("[pid err]", e)
        return None


def attach():
    dev = frida.get_device_manager().add_remote_device(HOST)
    pid = adb_pid()
    if pid:
        print(f"[*] attach by adb pid {pid}")
        return dev.attach(pid)
    print("[*] fallback: attach by name")
    return dev.attach(PKG)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "state"
    session = attach()
    with open(JS, "r", encoding="utf-8") as f:
        src = f.read()
    script = session.create_script(src)
    logs = []

    def on_msg(m, d):
        if m.get("type") == "send":
            logs.append(m.get("payload"))
        elif m.get("type") == "error":
            logs.append({"__error__": m.get("description")})
        else:
            logs.append(m)
    script.on("message", on_msg)
    script.load()
    time.sleep(0.6)
    try:
        if cmd == "ckheaders":
            res = script.exports.clientkeyheaders()
        elif cmd == "state":
            res = script.exports.state()
        elif cmd == "framesign":
            scene = sys.argv[2] if len(sys.argv) > 2 else "search"
            mode = int(sys.argv[3]) if len(sys.argv) > 3 else 0
            res = script.exports.framesign(scene, mode)
        elif cmd == "mstoken":
            res = script.exports.mstoken()
        elif cmd == "flow":
            # 触发搜索以捕获 MSManager 实例，然后调用 RPC
            kw = sys.argv[2] if len(sys.argv) > 2 else "rpcflow"
            print(f"[*] triggering search keyword={kw}")
            subprocess.run([ADB, "-s", SERIAL, "shell", "am", "start",
                            "-a", "android.intent.action.VIEW",
                            "-d", f"snssdk1128://search?keyword={kw}"],
                           capture_output=True, text=True, timeout=30)
            time.sleep(10)
            res = {"state": script.exports.state()}
            try:
                res["framesign_scene_search"] = script.exports.framesign("search", 0)
            except Exception as e:
                res["framesign_err"] = str(e)
            try:
                res["mstoken"] = script.exports.mstoken()
            except Exception as e:
                res["mstoken_err"] = str(e)
        else:
            res = {"_err": "unknown cmd"}
        print("=== RESULT ===")
        print(json.dumps(res, ensure_ascii=False, indent=2))
    except Exception as e:
        print("[RPC ERROR]", e)
    if logs:
        print("=== JS LOGS ===")
        for l in logs[:20]:
            print(l)
    session.detach()


if __name__ == "__main__":
    main()
