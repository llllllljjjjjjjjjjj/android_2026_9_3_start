# IDA 9.2: dump DoVerifyV2 + 内部调用者 + vtable + Engine_Create
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils, ida_bytes
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_certverify2.txt"


def dump_range(start, end, lines, maxcnt=600, indent="  "):
    e, cnt = start, 0
    while e < end and e != ida_idaapi.BADADDR and cnt < maxcnt:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%s%08x  %s" % (indent, e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, end + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1


def dump_func_at(ea, lines, maxcnt=600):
    fn = ida_funcs.get_func(ea)
    lines.append("=" * 70)
    if not fn:
        lines.append("(no func at %s)" % hex(ea))
        dump_range(ea, ea + 0x100, lines, 40)
        return
    fname = idc.get_func_name(fn.start_ea)
    lines.append("func @ %s name=%s range=%s-%s" %
                 (hex(ea), fname, hex(fn.start_ea), hex(fn.end_ea)))
    dump_range(fn.start_ea, fn.end_ea, lines, maxcnt)


def dump_vtable(addr, n, lines, name):
    lines.append("=" * 70)
    lines.append("vtable %s @ %s:" % (name, hex(addr)))
    for i in range(n):
        ptr = ida_bytes.get_qword(addr + 8 * i)
        nm = idc.get_name(ptr) if ptr else ""
        lines.append("  [%d] 0x%08x  %s" % (i, ptr, nm))


def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []

    dump_func_at(0x277114, lines, 600)          # DoVerifyV2
    dump_func_at(0x26ff64, lines, 500)          # Cronet_Engine_Create
    dump_func_at(0x240e84, lines, 100)          # Cronet_CertVerify_Destroy

    # xrefs to DoVerifyV2
    lines.append("=" * 70)
    lines.append("xrefs to DoVerifyV2 (0x277114):")
    seen = set()
    for x in idautils.XrefsTo(0x277114):
        if x.frm in seen:
            continue
        seen.add(x.frm)
        f = ida_funcs.get_func(x.frm)
        if f:
            lines.append("  from func %08x (%s) call at %08x" %
                         (f.start_ea, idc.get_func_name(f.start_ea), x.frm))
        else:
            lines.append("  from %08x (no func)" % x.frm)
    # dump each caller func body (short)
    for x in list(idautils.XrefsTo(0x277114)):
        f = ida_funcs.get_func(x.frm)
        if f and f.start_ea not in dumped_callers:
            dumped_callers.add(f.start_ea)
            dump_func_at(f.start_ea, lines, 500)

    # xrefs to Cronet_CertVerify_Create (who creates default verifier)
    lines.append("=" * 70)
    lines.append("xrefs to Cronet_CertVerify_Create (0x27f53c):")
    for x in idautils.XrefsTo(0x27f53c):
        f = ida_funcs.get_func(x.frm)
        lines.append("  from %08x (%s)" % (x.frm, idc.get_func_name(f.start_ea) if f else "-"))

    dump_vtable(0x5D5B58, 8, lines, "CertVerify_CreateWith")
    dump_vtable(0x5D6060, 8, lines, "CertVerify_Create")

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


dumped_callers = set()
main()
