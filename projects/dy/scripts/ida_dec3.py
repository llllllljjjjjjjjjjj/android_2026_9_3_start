# IDA 9.2: libmetasec_ml_dec.so 第三轮 —— 核心函数反汇编（算法核心）
# 0x28065c 已解出：输入消息 = headers + 0x3E4F98const + url
#   unk_264E3C(out, mode, msg)  mode=1/2 -> 哈希核心
#   unk_274C60 = VMP 解释器
# 本轮: 反汇编这些函数 + 0x2810d4 VMP dispatcher + 数据表
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, ida_ua, ida_bytes, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_metasec_dec3.txt"

FUNCS = [
    (0x264E3C, 0x265200, "unk_264E3C  hash-core(out,mode,msg)"),
    (0x274C60, 0x274D00, "unk_274C60  VMP-interp"),
    (0x279444, 0x279540, "unk_279444  len"),
    (0x279D68, 0x279E40, "unk_279D68  append/copy"),
    (0x34C010, 0x34C100, "unk_34C010  alloc"),
    (0x34C4F0, 0x34C600, "unk_34C4F0  memset-ish"),
    (0x34BFE0, 0x34C010, "unk_34BFE0  free"),
    (0x34BEF0, 0x34BFE0, "unk_34BEF0  ???"),
    (0x282020, 0x282140, "unk_282020"),
    (0x282144, 0x282200, "unk_282144"),
    (0x181A50, 0x181B80, "unk_181A50  (url,glob,0)"),
    (0x168820, 0x168A00, "unk_168820  log/fmt"),
    (0x15F060, 0x15F100, "unk_15F060"),
]

def disasm_range(lines, r1, r2, tag):
    lines.append("--- disasm %x-%x %s ---" % (r1, r2, tag))
    made = 0
    for ea in range(r1, r2, 4):
        try:
            if idc.create_insn(ea):
                made += 1
        except Exception:
            pass
    lines.append("create_insn ok=%d / %d" % (made, (r2 - r1) // 4))
    ea = idc.next_head(r1 - 4, r2 + 4)
    if ea == ida_idaapi.BADADDR:
        ea = r1
    cnt = 0
    while ea != ida_idaapi.BADADDR and ea < r2 and cnt < 4000:
        dis = idc.generate_disasm_line(ea, 0)
        lines.append("%08x  %s" % (ea, dis))
        nxt = idc.next_head(ea, r2 + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= ea:
            break
        sz = idc.get_item_size(ea)
        if nxt - ea != sz:
            b = ida_bytes.get_bytes(ea + sz, nxt - ea - sz)
            if b:
                lines.append("      gap %08x: DW %s" % (ea + sz, b.hex()))
        ea = nxt
        cnt += 1
    lines.append("")

def hexdump_range(lines, r1, r2, tag, ascii_on=True):
    lines.append("--- hexdump %x-%x %s ---" % (r1, r2, tag))
    for off in range(r1, r2, 16):
        b = ida_bytes.get_bytes(off, 16)
        if b:
            asc = "".join(chr(x) if 0x20 <= x < 0x7f else "." for x in b) if ascii_on else ""
            lines.append("%08x  %s  %s" % (off, " ".join("%02x" % x for x in b), asc))
    lines.append("")

def main():
    try:
        ida_auto.enable_auto(False)
    except Exception as e:
        print("enable_auto fail:", e)
    time.sleep(6)
    lines = []
    lines.append("--- sanity 0x28065c ---")
    b = ida_bytes.get_bytes(0x28065C, 16)
    lines.append("28065c: %s" % (b.hex() if b else "NONE"))
    lines.append("")
    for s in idautils.Segments():
        lines.append("seg: %08x-%08x %s" % (idc.get_segm_start(s), idc.get_segm_end(s), idc.get_segm_name(s)))
    lines.append("")

    # 0x28065c 主回调完整体 + 0x2810d4 VMP dispatcher
    disasm_range(lines, 0x28065C, 0x281400, "main cb 28065c")
    disasm_range(lines, 0x2810D4, 0x281C00, "VMP dispatcher 2810d4")

    for f1, f2, tag in FUNCS:
        disasm_range(lines, f1, f2, tag)

    # 数据表
    hexdump_range(lines, 0xA6000, 0xA7000, "str/fmt table a6000")
    hexdump_range(lines, 0x3E4F80, 0x3E5000, "globals 3e4f80")
    hexdump_range(lines, 0x3E5F80, 0x3E6200, "globals 3e5f80")

    # ascii 扫描 0xa6000-0xa7000
    lines.append("--- strings 0xa6000-0xa7000 ---")
    data = ida_bytes.get_bytes(0xA6000, 0x1000)
    if data:
        i = 0
        while i < len(data):
            if 0x20 <= data[i] < 0x7f:
                j = i
                while j < len(data) and 0x20 <= data[j] < 0x7f:
                    j += 1
                if j - i >= 4:
                    lines.append("%08x: %s" % (0xA6000 + i, data[i:j].decode("latin1")))
                i = j
            else:
                i += 1
    lines.append("")

    # add_func 尝试
    for ea, tag in [(0x28065C, "main"), (0x2810D4, "dispatcher"), (0x264E3C, "hash"), (0x274C60, "interp")]:
        try:
            r = ida_funcs.add_func(ea)
            lines.append("add_func(%x) %s -> %s" % (ea, tag, r))
        except Exception as e:
            lines.append("add_func(%x) fail: %s" % (ea, e))

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
