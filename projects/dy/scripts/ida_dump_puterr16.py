# IDA 9.2: dump libttboringssl.so 塞入 lib=16 reason=125 (handshake.cc:393) 的现场
# 运行期调用链: +0x38e84 <- +0x3a1f0 <- +0x394fc <- +0x486f8(SSL_do_handshake+0x38) <- libsscronet+0x3da4d0
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_puterr16.txt"
ADDRS = [0x38E84, 0x3A1F0, 0x394FC]   # 塞错误调用链
DO_HS = 0x486C0                        # SSL_do_handshake


def dump_range(start, end, lines, maxcnt=500, indent="  "):
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


def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []
    lines.append("input: %s" % idc.get_input_file_path())

    done = set()
    for ea in ADDRS:
        lines.append("=" * 70)
        fn = ida_funcs.get_func(ea)
        if not fn:
            lines.append("(no func at 0x%x)" % ea)
            dump_range(ea, ea + 0x200, lines, 60)
            continue
        if fn.start_ea in done:
            lines.append("0x%x 已在同一函数内: %s (%s-%s)" %
                         (ea, idc.get_func_name(fn.start_ea), hex(fn.start_ea), hex(fn.end_ea)))
            continue
        done.add(fn.start_ea)
        lines.append("func @%s name=%s range=%s-%s  (target 0x%x 相对偏移 +0x%x)" %
                     (hex(fn.start_ea), idc.get_func_name(fn.start_ea),
                      hex(fn.start_ea), hex(fn.end_ea), ea, ea - fn.start_ea))
        dump_range(fn.start_ea, fn.end_ea, lines, 500)

    # SSL_do_handshake 本体（看它如何调 0x394fc）
    fn = ida_funcs.get_func(DO_HS)
    lines.append("=" * 70)
    if fn:
        lines.append("SSL_do_handshake func name=%s range=%s-%s" %
                     (idc.get_func_name(fn.start_ea), hex(fn.start_ea), hex(fn.end_ea)))
        dump_range(fn.start_ea, fn.end_ea, lines, 400)
    else:
        lines.append("(no func at 0x%x)" % DO_HS)

    # 0x3a1f0 / 0x394fc 若不在已 dump 函数里则单独看
    for ea in (0x3A1F0, 0x394FC):
        fn = ida_funcs.get_func(ea)
        if fn and fn.start_ea not in done:
            done.add(fn.start_ea)
            lines.append("=" * 70)
            lines.append("caller func @%s name=%s range=%s-%s" %
                         (hex(fn.start_ea), idc.get_func_name(fn.start_ea),
                          hex(fn.start_ea), hex(fn.end_ea)))
            dump_range(fn.start_ea, fn.end_ea, lines, 300)

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
