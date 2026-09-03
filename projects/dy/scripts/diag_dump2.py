# -*- coding: utf-8 -*-
import subprocess

ADB = r"D:\reserve_agent\ish-portable-kit\android_mcp\toolchain\bin\windows\platform-tools\adb.exe"


def run(cmd, timeout=60):
    r = subprocess.run([ADB, "shell", "su", "-c", cmd],
                       capture_output=True, text=True, timeout=timeout)
    return r.stdout, r.stderr


pid = subprocess.check_output([ADB, "shell", "pidof", "com.ss.android.ugc.aweme"]).decode().split()[0]
print("pid", pid)

# 0x 算术
o, e = run("s=12c00000; echo $((0x$s))")
print("hex 0x:", repr(o.strip()), repr(e.strip()))

# dd 第一个 rw-p 段：12c00000 起，skip=0x12c00000/4096
o, e = run(f"dd if=/proc/{pid}/mem of=/data/local/tmp/test2.bin bs=4096 skip=$((0x12c00000/4096)) count=3 2>&1; ls -l /data/local/tmp/test2.bin")
print("--- dd correct skip ---")
print("stdout:", o)
print("stderr:", e)

# 完整脚本逻辑（第一行 rw-p 段）
o, e = run(f"""
out=/data/local/tmp/dump2.bin; lst=/data/local/tmp/dump2.lst
: > $out; : > $lst
n=0
while read s e p rest; do
  case "$p" in
    rw-p)
      s=$((0x$s)); e=$((0x$e)); sz=$((e-s))
      if [ $sz -gt 65536 ]; then
        off=$(stat -c %s $out)
        dd if=/proc/{pid}/mem bs=4096 skip=$((s/4096)) count=$((sz/4096)) >> $out 2>/dev/null
        echo "$s $e $off" >> $lst
        n=$((n+1))
      fi
      ;;
  esac
done < /proc/{pid}/maps
echo "segments=$n"
ls -l $out $lst
""")
print("--- full loop ---")
print(o)
print(e)
