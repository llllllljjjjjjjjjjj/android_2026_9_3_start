# IDA 9.2: xrefs to setter sub_26D220/26D234 + 调用者函数 dump
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_regcall.txt"

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
    lines.append("--- xrefs to sub_26D220 ---")
    for x in idautils.XrefsTo(0x26d220):
        lines.append("26d220 <- %08x (%s)" % (x.frm, x.type))
    lines.append("--- xrefs to sub_26D234 ---")
    for x in idautils.XrefsTo(0x26d234):
        lines.append("26d234 <- %08x (%s)" % (x.frm, x.type))
    lines.append("--- xrefs to sub_26D248 (x-ss-stub MD5 链) ---")
    for x in idautils.XrefsTo(0x26d248):
        lines.append("26d248 <- %08x (%s)" % (x.frm, x.type))
    lines.append("")
    # dump 调用者
    seen = set()
    for tgt in [0x26d220, 0x26d234]:
        for x in idautils.XrefsTo(tgt):
            if x.frm not in seen:
                seen.add(x.frm)
                dump_func(x.frm, lines)
    with open(OUT, "w") as fh:
        fh.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
