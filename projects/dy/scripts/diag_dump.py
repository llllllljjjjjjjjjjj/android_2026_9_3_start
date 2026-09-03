# -*- coding: utf-8 -*-
import subprocess
import sys

ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"


def run(cmd):
    r = subprocess.run([ADB, "shell", "su", "-c", cmd],
                       capture_output=True, text=True, timeout=30)
    return r.stdout, r.stderr


pid = subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0]
print("pid", pid)

# 1) dd 单段
o, e = run(f"dd if=/proc/{pid}/mem of=/data/local/tmp/test.bin bs=4096 skip=30720 count=2 2>&1; ls -l /data/local/tmp/test.bin")
print("--- dd test ---")
print("stdout:", o)
print("stderr:", e)

# 2) hex 算术
o, e = run("s=12c00000; echo $((16#$s))")
print("--- hex test ---")
print("stdout:", repr(o))
print("stderr:", repr(e))

# 3) 看 maps 第一行 rw-p 段
o, e = run(f"head -5 /proc/{pid}/maps")
print("--- maps head ---")
print(o)
