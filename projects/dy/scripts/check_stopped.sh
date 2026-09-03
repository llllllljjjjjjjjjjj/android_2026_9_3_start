#!/system/bin/sh
# 检查 aweme 进程中被 SIGSTOP 的线程 (state=T/t), 验证 gum-js-loop 冻结假设
P=${1:-0}
if [ "$P" = "0" ] || [ ! -d /proc/$P ]; then
  P=$(pidof com.ss.android.ugc.aweme | awk '{print $1}')
fi
if [ -z "$P" ] || [ ! -d /proc/$P ]; then
  echo "app not running"
  exit 1
fi
echo "== pid $P (comm: $(cat /proc/$P/comm 2>/dev/null)) =="
n=0
for t in /proc/$P/task/*; do
  st=$(cat $t/stat 2>/dev/null)
  state=$(echo "$st" | awk '{print $3}')
  if [ "$state" = "T" ] || [ "$state" = "t" ]; then
    tid=${t##*/}
    name=$(cat $t/comm 2>/dev/null)
    echo "STOPPED tid=$tid state=$state comm=$name"
    n=$((n+1))
  fi
done
echo "stopped_count=$n"
echo "--- state histogram (R=running S=sleeping D=disk T=stopped Z=zombie) ---"
for t in /proc/$P/task/*; do
  cat $t/stat 2>/dev/null | awk '{print $3}'
done | sort | uniq -c
