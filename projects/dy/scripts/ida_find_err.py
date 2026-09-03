# IDA 9.2: 在 libttboringssl.so 中搜索错误码常量 0x230000CA（lib=35 reason=202 的打包值）
# 定位"第二道证书校验"：找到引用该常量的代码 → dump 所在函数
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils, ida_bytes, ida_segment
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_err35.txt"

TARGET = 0x230000CA  # 也试无 line 的 0x23000000 变体


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
        dump_range(ea, ea + 0x300, lines, 80)
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

    # 1) rodata 里搜索 dword 0x230000CA（小端: CA 00 00 23）
    hits = []
    for i in range(ida_segment.get_segm_qty()):
        seg = ida_segment.getnseg(i)
        if not seg:
            continue
        sname = ida_segment.get_segm_name(seg)
        if sname not in (".rodata", ".data.rel.ro", ".data", "LOAD"):
            # 遍历所有段太慢，只扫只读段
            if not (seg.perm & 4) and (seg.perm & 1):
                pass
            else:
                continue
        ea = seg.start_ea
        end = seg.end_ea
        while ea < end and ea != ida_idaapi.BADADDR:
            v = ida_bytes.get_dword(ea)
            if v == TARGET:
                hits.append(ea)
            ea += 4
    lines.append("dword 0x230000CA in rodata hits: %s" % [hex(h) for h in hits])

    # 2) xref 这些 rodata 位置
    xref_sites = []
    for h in hits:
        for x in idautils.XrefsTo(h):
            xref_sites.append(x.frm)
    lines.append("xref sites: %s" % [hex(x) for x in xref_sites])

    # 3) dump 引用处的函数
    done = set()
    for x in xref_sites:
        fn = ida_funcs.get_func(x)
        if not fn or fn.start_ea in done:
            continue
        done.add(fn.start_ea)
        dump_func_at(x, lines, 400, "= refs 0x230000CA")

    # 4) 文本反汇编搜索立即数 #0x230000CA 或 MOVK 片段
    lines.append("=" * 70)
    lines.append("text scan for immediates 0x230000CA / 0x230000 fragments:")
    cnt = 0
    for i in range(ida_segment.get_segm_qty()):
        seg = ida_segment.getnseg(i)
        if not seg or ida_segment.get_segm_name(seg) != ".text":
            continue
        ea = seg.start_ea
        end = seg.end_ea
        while ea < end and ea != ida_idaapi.BADADDR and cnt < 40:
            dis = idc.generate_disasm_line(ea, 0)
            if "230000CA" in dis or "230000" in dis:
                lines.append("%08x  %s" % (ea, dis))
                fn = ida_funcs.get_func(ea)
                if fn:
                    lines.append("    (in func %s @ %s)" %
                                 (idc.get_func_name(fn.start_ea), hex(fn.start_ea)))
                cnt += 1
            nxt = idc.next_head(ea, ida_idaapi.BADADDR)
            if nxt == ida_idaapi.BADADDR or nxt <= ea:
                break
            ea = nxt
        if cnt >= 40:
            break

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
