# IDA 9.2: dump libttboringssl.so 的 verify 相关函数（获取结构体偏移）
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_ttboring.txt"


def dump_range(start, end, lines, maxcnt=200, indent="  "):
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


def dump_name(name, lines):
    ea = idc.get_name_ea_simple(name)
    lines.append("=" * 70)
    if ea == ida_idaapi.BADADDR:
        lines.append("%s: NOT FOUND" % name)
        return
    fn = ida_funcs.get_func(ea)
    lines.append("func %s @ %s" % (name, hex(ea)))
    if fn:
        dump_range(fn.start_ea, fn.end_ea, lines, 200)
    else:
        dump_range(ea, ea + 0x80, lines, 40)


def main():
    ida_auto.auto_wait()
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []
    for n in ["SSL_CTX_set_custom_verify", "SSL_set_custom_verify",
              "SSL_CTX_set_verify", "SSL_get_verify_result",
              "SSL_get_servername"]:
        dump_name(n, lines)
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
