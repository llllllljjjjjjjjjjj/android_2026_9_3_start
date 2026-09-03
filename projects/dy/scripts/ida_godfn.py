# IDA 9.2: dump 神头写入函数 libsscronet.so+47a31c 全量反汇编 + BL 目标 + xrefs
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_godfn_47a31c.txt"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    ea = 0x47a31c
    fn = ida_funcs.get_func(ea)
    if not fn:
        print("no func at", hex(ea))
        ida_pro.qexit(1)
    lines = []
    lines.append("func: %s - %s (name: %s)" % (hex(fn.start_ea), hex(fn.end_ea), idc.get_func_name(fn.start_ea)))
    e = fn.start_ea
    cnt = 0
    while e < fn.end_ea and e != ida_idaapi.BADADDR and cnt < 3000:
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
    lines.append("--- call targets ---")
    for (s, e2) in idautils.Chunks(fn.start_ea):
        p = s
        while p < e2 and p != ida_idaapi.BADADDR:
            if idc.print_insn_mnem(p) == "BL":
                t = idc.get_operand_value(p, 0)
                nm = idc.get_name(t)
                lines.append("%08x BL %s (%s)" % (p, hex(t), nm))
            p = idc.next_head(p, fn.end_ea + 4)
            if p == ida_idaapi.BADADDR:
                break
    lines.append("")
    lines.append("--- xrefs to this func ---")
    for x in idautils.XrefsTo(fn.start_ea):
        lines.append("%08x <- %08x (%s)" % (fn.start_ea, x.frm, x.type))
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
