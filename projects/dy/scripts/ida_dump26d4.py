# IDA 9.2: dump sub_26D4D0 (0x26d4d0-0x26d7c0)
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi
import time
OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_dump26d4.txt"
def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    fn = ida_funcs.get_func(0x26d4d0)
    lines = []
    if not fn:
        lines.append("no func")
    else:
        e, cnt = fn.start_ea, 0
        while e < fn.end_ea and e != ida_idaapi.BADADDR and cnt < 2500:
            dis = idc.generate_disasm_line(e, 0)
            cmt = idc.get_cmt(e, 0)
            line = "%08x  %s" % (e, dis)
            if cmt: line += "  ; " + cmt
            lines.append(line)
            nxt = idc.next_head(e, fn.end_ea + 4)
            if nxt == ida_idaapi.BADADDR or nxt <= e: break
            e = nxt; cnt += 1
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines))
    print("wrote", len(lines))
    ida_pro.qexit(0)
try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
