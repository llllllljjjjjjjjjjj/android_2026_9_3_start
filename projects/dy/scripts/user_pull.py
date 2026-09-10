# -*- coding: utf-8 -*-
"""用户主页：按 uid 拉取用户资料（昵称/粉丝/作品数等）

用法:
  python user_pull.py <uid> [more_uids...]
  python user_pull.py --from results_冲浪.json 3      (取前 3 条的 uid)
"""
import sys, json, time, subprocess, os
import frida

HOST = "127.0.0.1:27042"
JS = r"D:\reserve_agent\android\projects\dy\hooks\hook_user_rpc.js"
PKG = "com.ss.android.ugc.aweme"
ADB = r"D:\reserve_agent\android\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"
SERIAL = "9C181EC3BF7E0D"
OUTDIR = r"D:\reserve_agent\android\projects\dy\capture"


def adb(*a, timeout=30):
    return subprocess.run([ADB, "-s", SERIAL] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="ignore", timeout=timeout)


def attach_script(retries=3):
    for i in range(retries):
        try:
            dev = frida.get_device_manager().add_remote_device(HOST)
            pid = (adb("shell", "pidof", PKG).stdout or "").strip().split()
            session = dev.attach(int(pid[0])) if pid else dev.attach(PKG)
            script = session.create_script(open(JS, encoding="utf-8").read())
            script.on("message", lambda m, d: None)
            script.load()
            time.sleep(0.6)
            return session, script
        except Exception as e:
            print(f"[!] attach {i+1}/{retries} failed: {e}")
            time.sleep(3 * (i + 1))
    return None, None


def main():
    args = sys.argv[1:]
    uids = []
    if args and args[0] == "--from":
        src = os.path.join(OUTDIR, args[1])
        n = int(args[2]) if len(args) > 2 else 3
        data = json.load(open(src, encoding="utf-8"))
        uids = [c["uid"] for c in data if c.get("uid")][:n]
    else:
        uids = [a for a in args if a.isdigit()]

    if not uids:
        print("usage: user_pull.py <uid>... | --from <results_x.json> [n]")
        return 1

    session, script = attach_script()
    if not session:
        print("[!] abort")
        return 1
    try:
        script.exports_sync.clear()
        for i, uid in enumerate(uids, 1):
            deep = f"snssdk1128://user/profile/{uid}"
            adb("shell", "am", "start", "-a", "android.intent.action.VIEW", "-d", deep)
            time.sleep(6)
            print(f"[*] {i}/{len(uids)} opened uid={uid}, collected={script.exports_sync.count()}")
            if i < len(uids):
                adb("shell", "input", "keyevent", "4")   # BACK
                time.sleep(1.5)
        data = script.exports_sync.getlist()
        out = os.path.join(OUTDIR, "users.json")
        json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"[*] users: {len(data)} -> {out}")
        for u in data[:8]:
            print(f"    uid={u['uid']} {u.get('nickname')} 粉丝={u.get('follower')} 作品={u.get('awemeCount')} 获赞={u.get('totalFavorited')}")
        return 0
    finally:
        try:
            session.detach()
        except Exception:
            pass


if __name__ == "__main__":
    sys.exit(main())
