# IDA 9.2: dump libttboringssl.so 的 SSL_get_error（0x4901c）+ sscronet 的 sub_3DB8EC（ssl→net 错误映射）
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_sslgeterror.txt"


def dump_range(start, end, lines, maxcnt=600, indent="  "):
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


def dump_func_at(ea, lines, maxcnt=600, tag=""):
    fn = ida_funcs.get_func(ea)
    lines.append("=" * 70)
    if not fn:
        lines.append("(no func at %s, linear dump) %s" % (hex(ea), tag))
        dump_range(ea, ea + 0x200, lines, 60)
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
    inp = idc.get_input_file_path()
    lines.append("input: %s" % inp)
    if "libttboringssl.so" in inp:
        dump_func_at(0x4901c, lines, 600, "= SSL_get_error (tt 魔改，含 13/16 自定义码)")
    elif "libsscronet.so" in inp:
        dump_func_at(0x3DB8EC, lines, 600, "= sub_3DB8EC (ssl error → net error 映射)")
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
