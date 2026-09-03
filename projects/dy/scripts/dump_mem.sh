#!/system/bin/sh
# dump_mem.sh — 零注入 dump App 进程 rw 内存区域到 /data/local/tmp/memdump/
# 用法: sh dump_mem.sh <pid>
PID=$1
OUT=/data/local/tmp/memdump
mkdir -p $OUT
rm -f $OUT/*.bin 2>/dev/null
N=0
grep -E 'rw-[ps]' /proc/$PID/maps | while read line; do
  RANGE=$(echo "$line" | cut -d' ' -f1)
  START=$(echo "$RANGE" | cut -d'-' -f1)
  END=$(echo "$RANGE" | cut -d'-' -f2)
  S=$((16#$START))
  E=$((16#$END))
  SZ=$((E-S))
  # 只 dump 64KB - 128MB 区域
  if [ $SZ -lt 65536 ] || [ $SZ -gt 134217728 ]; then continue; fi
  N=$((N+1))
  SKIP=$((S/4096))
  CNT=$((SZ/4096))
  dd if=/proc/$PID/mem of=$OUT/seg_$(printf '%05d' $N)_$START.bin bs=4096 skip=$SKIP count=$CNT 2>/dev/null
done
echo "done $N segs -> $OUT"
