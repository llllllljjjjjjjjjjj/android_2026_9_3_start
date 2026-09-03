# IDA 9.2: qword_5FFE80/5FFE88 数据 xref (谁注册 metasec 回调) + 47A31C 相邻辅助函数
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_bridge.txt"

def dump_func(fstart, lines):
    fn = ida_funcs.get_func(fstart)
    if not fn:
        lines.append("no func at %x" % fstart)
        lines.append("")
        return
    lines.append("== func %x - %x (name: %s)" % (fn.start_ea, fn.end_ea, idc.get_func_name(fn.start_ea)))
    e = fn.start_ea
    cnt = 0
    while e < fn.end_ea and e != ida_idaapi.BADADDR and cnt < 800:
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
    lines.append("--- xrefs to qword_5FFE80 ---")
    for x in idautils.XrefsTo(0x5FFE80):
        lines.append("5FFE80 <- %08x (%s)" % (x.frm, x.type))
    lines.append("")
    lines.append("--- xrefs to qword_5FFE88 ---")
    for x in idautils.XrefsTo(0x5FFE88):
        lines.append("5FFE88 <- %08x (%s)" % (x.frm, x.type))
    lines.append("")
    for f in [0x47AF90, 0x47B598, 0x47B740, 0x47BA98]:
        dump_func(f, lines)
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
