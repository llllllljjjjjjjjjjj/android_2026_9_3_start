# IDA 9.2: dump libsscronet.so 握手调用方区域（0x3da4d0 / 0x3dc1b0 / 0x3d9f40）
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_sscronet_hs.txt"


def dump_range(start, end, lines, maxcnt=400, indent="  "):
    e, cnt = start, 0
    while e < end and e != ida_idaapi.BADADDR and cnt < maxcnt:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%s%08x  %s" % (indent, e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, ida_idaapi.BADADDR)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1


def dump_func_at(ea, lines, maxcnt=400, tag=""):
    fn = ida_funcs.get_func(ea)
    lines.append("=" * 70)
    if not fn:
        lines.append("(no func at %s, linear dump) %s" % (hex(ea), tag))
        dump_range(ea, ea + 0x400, lines, 80)
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
    dump_func_at(0x3da4d0, lines, 500, "= handshake caller (ret addr after SSL_do_handshake)")
    dump_func_at(0x3dc1b0, lines, 300, "= BT frame 2 (0x3dc1b0)")
    dump_func_at(0x3d9f40, lines, 300, "= BT frame 2 alt (0x3d9f40)")
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
