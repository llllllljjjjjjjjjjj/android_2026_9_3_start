# IDA 9.2: libmetasec_ml_dec.so 第四轮 —— 补齐 hash 主体 + VMP 解释器主体 + 关键 helper
# 上轮缺口：
#   264E3C 的 hash 主体在 265200 之后（栈分配之后的真正逻辑）
#   274C60 的 VMP 解释器主体在 274D00 之后
#   helper: 271F7C / 25BE84(url query) / 15FF4C,163228,1632B0,15EB74(std::string) / 266A24 / 165EAC / 165E80
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, ida_ua, ida_bytes, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_metasec_dec4.txt"

FUNCS = [
    (0x265200, 0x267000, "264E3C body 265200 hash-main"),
    (0x274D00, 0x276800, "274C60 body 274d00 VMP-interp-main"),
    (0x271F7C, 0x272080, "unk_271F7C  check-ret-helper"),
    (0x25BE84, 0x25C100, "unk_25BE84  url-query-extract"),
    (0x266A24, 0x266C00, "unk_266A24  alloc20-helper"),
    (0x165EAC, 0x166000, "unk_165EAC"),
    (0x165E80, 0x165EAC, "unk_165E80"),
    (0x15FF4C, 0x160000, "unk_15FF4C  str-helper1"),
    (0x163228, 0x163300, "unk_163228  str-helper2"),
    (0x1632B0, 0x163340, "unk_1632B0  str-helper3"),
    (0x15EB74, 0x15EC00, "unk_15EB74  str-helper4"),
    (0x26FAFC, 0x26FC74, "unk_26FAFC"),
    (0x26FC74, 0x26FD00, "unk_26FC74"),
    (0x167894, 0x167980, "unk_167894"),
    (0x25FDD4, 0x25FE60, "unk_25FDD4"),
    (0x25FDDC, 0x25FE60, "unk_25FDDC"),
    (0x25FDE4, 0x25FE80, "unk_25FDE4"),
    (0x1647A8, 0x164900, "unk_1647A8"),
    (0x282170, 0x282800, "unk_282170"),
    (0x282C20, 0x283200, "unk_282C20"),
]

def disasm_range(lines, r1, r2, tag, maxcnt=8000):
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
    while ea != ida_idaapi.BADADDR and ea < r2 and cnt < maxcnt:
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

def hexdump_range(lines, r1, r2, tag):
    lines.append("--- hexdump %x-%x %s ---" % (r1, r2, tag))
    for off in range(r1, r2, 16):
        b = ida_bytes.get_bytes(off, 16)
        if b:
            asc = "".join(chr(x) if 0x20 <= x < 0x7f else "." for x in b)
            lines.append("%08x  %s  %s" % (off, " ".join("%02x" % x for x in b), asc))
    lines.append("")

def main():
    try:
        ida_auto.enable_auto(False)
    except Exception as e:
        print("enable_auto fail:", e)
    time.sleep(6)
    lines = []
    for f1, f2, tag in FUNCS:
        disasm_range(lines, f1, f2, tag)

    # 数据表：VMP 绑定表 + handler 表区
    hexdump_range(lines, 0xAA80, 0xAE80, "vmp-bind table aa80")
    # 264F54 用到的 XOR 解码数据区（密文/密钥/输出）
    hexdump_range(lines, 0x9A0C80, 0x9A0E00, "xor-decode data 9a0c80")
    hexdump_range(lines, 0x3E31A0, 0x3E3200, "xor-decode keys 3e31a0 (bss)")
    # 置换表
    hexdump_range(lines, 0xA61F0, 0xA6400, "perm table a61f0")
    hexdump_range(lines, 0xA68F0, 0xA6960, "perm table a68f0")

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
