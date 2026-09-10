# -*- coding: utf-8 -*-
"""监控 reverse_index 建索引 + 全量清单任务是否完成。
完成判据:
  - manifest: projects/dy/artifacts/all_java_files.txt 存在且 > 100 字节
  - index: reverse_index.sqlite 主库 > 4096 (已 checkpoint) 且 WAL 不再增长,
           或 WAL 连续 N 个周期不增长(worker 完成)
每 30s 检查一次; 最长 2h; 两者均完成即退出打印总结。
"""
import os, time, sys

ART = r"projects\dy\artifacts"
DB = os.path.join(ART, "reverse_index.sqlite")
WAL = DB + "-wal"
MAN = os.path.join(ART, "all_java_files.txt")

def size(p):
    try:
        return os.path.getsize(p)
    except OSError:
        return -1

def check():
    db, wal = size(DB), size(WAL)
    man = size(MAN)
    man_done = man > 100
    # index done: db checkpointed (db grew) OR wal frozen 3+ rounds
    return db, wal, man, man_done

db0, wal0, man0, _ = check()
frozen_rounds = 0
t0 = time.time()
print(f"watch start: db={db0} wal={wal0} manifest={man0}", flush=True)
man_done = False
idx_done = False
while time.time() - t0 < 7200:
    time.sleep(30)
    db, wal, man, md = check()
    if md:
        man_done = True
    if wal == wal0 and wal > 0 and db == db0:
        frozen_rounds += 1
    else:
        frozen_rounds = 0
    if wal == wal0 and wal > 0 and frozen_rounds >= 6:
        idx_done = True
    # checkpointed (db grew beyond 4096) also means worker finished
    if db > 4096 and wal < wal0:
        idx_done = True
    db0, wal0 = db, wal
    print(f"t+{int(time.time()-t0)}s db={db} wal={wal} man={man} idx_done={idx_done} man_done={man_done}", flush=True)
    if man_done and idx_done:
        print("ALL DONE", flush=True)
        sys.exit(0)

print("TIMEOUT after 2h — not finished", flush=True)
sys.exit(1)
