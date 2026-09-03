# IDA 9.2: dump 真实校验函数 sub_27EC40 / CreateWith verify trampoline 0x2771d4 / engine ctor sub_26931C
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils, ida_bytes
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_certverify3.txt"


def dump_range(start, end, lines, maxcnt=800, indent="  "):
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


def dump_func_at(ea, lines, maxcnt=800, tag=""):
    fn = ida_funcs.get_func(ea)
    lines.append("=" * 70)
    if not fn:
        lines.append("(no func at %s) %s" % (hex(ea), tag))
        dump_range(ea, ea + 0x100, lines, 40)
        return
    fname = idc.get_func_name(fn.start_ea)
    lines.append("func @ %s name=%s range=%s-%s %s" %
                 (hex(ea), fname, hex(fn.start_ea), hex(fn.end_ea), tag))
    dump_range(fn.start_ea, fn.end_ea, lines, maxcnt)


def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []
    dump_func_at(0x27EC40, lines, 800, "= real DoVerifyV2 impl")
    dump_func_at(0x2771d4, lines, 200, "= CreateWith verify trampoline")
    dump_func_at(0x27EA7C, lines, 200, "= default CertVerify vtable[0]")
    dump_func_at(0x26931C, lines, 300, "= engine ctor")
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
