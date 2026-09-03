# IDA 9.2: dump libvcn.so 校验相关函数（带符号）+ libvcnverify.so 全文
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils, ida_segment
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_vcn.txt"

LIBS = {
    "libvcn.so": [
        "_Z17vcnDoCustomVerifyPvS_PKci",       # vcnDoCustomVerify
        "vcn_ssl_certs_verify",                 # 证书校验本体
        "set_vcn_custom_verify_callback",
        "is_has_vcn_custom_verify_callback",
        "vcn_url_socket_ssl_init",
    ],
}


def dump_range(start, end, lines, maxcnt=1500, indent="  "):
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


def dump_func_at(ea, lines, maxcnt=1500, tag=""):
    fn = ida_funcs.get_func(ea)
    lines.append("=" * 70)
    if not fn:
        lines.append("(no func at %s, linear dump) %s" % (hex(ea), tag))
        dump_range(ea, ea + 0x2000, lines, maxcnt)
        return
    fname = idc.get_func_name(fn.start_ea)
    lines.append("func @ %s name=%s range=%s-%s %s" %
                 (hex(ea), fname, hex(fn.start_ea), hex(fn.end_ea), tag))
    dump_range(fn.start_ea, fn.end_ea, lines, maxcnt)


def main():
    # 强制完整自动分析
    ida_auto.auto_wait()
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []
    inp = idc.get_input_file_path()
    lines.append("input: %s" % inp)
    if "libvcnverify" in inp:
        lines.append("=" * 70)
        lines.append("full .text dump of libvcnverify.so:")
        for i in range(ida_segment.get_segm_qty()):
            seg = ida_segment.getnseg(i)
            if seg and ida_segment.get_segm_name(seg) == ".text":
                dump_range(seg.start_ea, seg.end_ea, lines, 8000)
    elif "libvcn.so" in inp:
        for n in LIBS["libvcn.so"]:
            ea = idc.get_name_ea_simple(n)
            if ea == ida_idaapi.BADADDR:
                lines.append("=" * 70)
                lines.append("%s: NOT FOUND" % n)
                continue
            dump_func_at(ea, lines, 1500, n)
            lines.append("")
            lines.append("--- xrefs to %s (%s) ---" % (n, hex(ea)))
            for x in idautils.XrefsTo(ea):
                lines.append("  from %08x (%s)" % (x.frm, idc.get_func_name(x.frm) if ida_funcs.get_func(x.frm) else "-"))
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
