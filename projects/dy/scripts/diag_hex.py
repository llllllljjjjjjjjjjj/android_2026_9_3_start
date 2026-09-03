# -*- coding: utf-8 -*-
import subprocess

ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"

sh = """#!/system/bin/sh
s=12c00000
e=15140000
echo "s=$s"
echo "literal=$((0x12c00000))"
echo "varconcat=$((0x$s))"
echo "printf=$(printf %d 0x$s)"
echo "printf_e=$(printf %d 0x$e)"
"""

with open(r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\test_hex.sh",
          "w", encoding="utf-8", newline="\n") as f:
    f.write(sh)

subprocess.check_call([ADB, "push",
                       r"D:\reserve_agent\ish-portable-kit\projects\dy\capture\test_hex.sh",
                       "/data/local/tmp/test_hex.sh"], stdout=subprocess.DEVNULL)
r = subprocess.run([ADB, "shell", "su", "-c", "sh /data/local/tmp/test_hex.sh"],
                   capture_output=True, text=True, timeout=30)
print(r.stdout)
print(r.stderr)
