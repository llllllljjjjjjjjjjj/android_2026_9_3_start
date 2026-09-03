# IDA 9.2: dump 0x26d224 所在函数 (qword_5FFE80 注册点) + 0x26d000-0x26d500 全部函数边界
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_reg26d2.txt"

def dump_func(fstart, lines, maxins=2500):
    fn = ida_funcs.get_func(fstart)
    if not fn:
        lines.append("no func at %x" % fstart)
        return
    lines.append("== func %x - %x (name: %s)" % (fn.start_ea, fn.end_ea, idc.get_func_name(fn.start_ea)))
    e = fn.start_ea
    cnt = 0
    while e < fn.end_ea and e != ida_idaapi.BADADDR and cnt < maxins:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%08x  %s" % (e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1
    lines.append("")

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    lines = []
    lines.append("--- func list 0x26d000-0x26d500 ---")
    ea = 0x26d000
    while ea < 0x26d500:
        fn = ida_funcs.get_func(ea)
        if fn and fn.start_ea >= 0x26d000:
            lines.append("func %x - %x (%s)" % (fn.start_ea, fn.end_ea, idc.get_func_name(fn.start_ea)))
            ea = fn.end_ea
        else:
            ea += 4
    lines.append("")
    dump_func(0x26d224, lines)
    lines.append("--- xrefs to qword_5FFE78 ---")
    for x in idautils.XrefsTo(0x5FFE78):
        lines.append("5FFE78 <- %08x (%s)" % (x.frm, x.type))
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
