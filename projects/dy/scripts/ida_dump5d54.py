# IDA 9.2: dump 0x5d5300-0x5d5900 原始反汇编 (找 5d5470/78/88 所在函数)
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_dump5d54.txt"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    lines = []
    # 先找覆盖 5d5470 的函数 (可能函数边界在更早处)
    fn = ida_funcs.get_func(0x5d5470)
    if fn:
        lines.append("containing func: %x - %x (%s)" % (fn.start_ea, fn.end_ea, idc.get_func_name(fn.start_ea)))
        start, end = fn.start_ea, fn.end_ea
    else:
        lines.append("no containing func, raw dump 0x5d5300-0x5d5900")
        start, end = 0x5d5300, 0x5d5900
    e = start
    cnt = 0
    while e < end and e != ida_idaapi.BADADDR and cnt < 2000:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%08x  %s" % (e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, end + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
