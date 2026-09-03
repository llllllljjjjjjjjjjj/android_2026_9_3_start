# IDA 9.2: 分析 libmetasec_ml_dec.so（合并了解密代码 + 运行时 BSS，filesz 已扩展）
# 修 v1 的 3 个问题：
#   1) rwxp 页已合并 -> 0x28065c 不再是 0xFF
#   2) idautils.Strings API 变化 -> 手工 ASCII 扫描
#   3) 线性反汇编用 decode_insn 步进（跨 ret-CFG 数据岛）
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, ida_ua, ida_bytes, idautils, ida_segment
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_metasec_dec2.txt"

def main():
    try:
        ida_auto.enable_auto(False)
    except Exception as e:
        print("enable_auto fail:", e)
    time.sleep(6)
    lines = []
    lines.append("--- sanity: bytes at 0x28065c ---")
    b = ida_bytes.get_bytes(0x28065C, 16)
    lines.append("28065c: %s" % (b.hex() if b else "NONE"))
    lines.append("")

    # 段列表
    lines.append("--- segments ---")
    for s in idautils.Segments():
        lines.append("%08x-%08x %s" % (idc.get_segm_start(s), idc.get_segm_end(s), idc.get_segm_name(s)))
    lines.append("")

    # 1) 线性反汇编 0x28065c - 0x281400（rwxp 页 + seg2 开头续接）
    # 先 create_insn 建指令（undefined 字节 generate_disasm_line 只出 DCB）
    R1, R2 = 0x28065C, 0x281400
    lines.append("--- disasm %x-%x (linear, create_insn) ---" % (R1, R2))
    made = 0
    for ea in range(R1, R2, 4):
        try:
            if idc.create_insn(ea):
                made += 1
        except Exception:
            pass
    lines.append("create_insn ok=%d / %d" % (made, (R2 - R1) // 4))
    ea = idc.next_head(R1 - 4, R2 + 4)
    if ea == ida_idaapi.BADADDR:
        ea = R1
    cnt = 0
    while ea != ida_idaapi.BADADDR and ea < R2 and cnt < 3000:
        dis = idc.generate_disasm_line(ea, 0)
        lines.append("%08x  %s" % (ea, dis))
        nxt = idc.next_head(ea, R2 + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= ea:
            break
        sz = idc.get_item_size(ea)
        if nxt - ea != sz:  # 数据岛（create_insn 失败处）
            b = ida_bytes.get_bytes(ea + sz, nxt - ea - sz)
            if b:
                lines.append("      gap %08x: DW %s" % (ea + sz, b.hex()))
        ea = nxt
        cnt += 1
    lines.append("")

    # 2) 数据区 0xaa8c (adrp x0 -> +0xa8c 引用的配置区)
    lines.append("--- data 0xaa80-0xae80 ---")
    for off in range(0xAA80, 0xAE80, 16):
        b = ida_bytes.get_bytes(off, 16)
        if b:
            asc = "".join(chr(x) if 0x20 <= x < 0x7f else "." for x in b)
            lines.append("%08x  %s  %s" % (off, " ".join("%02x" % x for x in b), asc))
    lines.append("")

    # 3) 全局区 0x3e5f80-0x3e6200 (状态机全局)
    lines.append("--- globals 0x3e5f80-0x3e6200 ---")
    for off in range(0x3E5F80, 0x3E6200, 16):
        b = ida_bytes.get_bytes(off, 16)
        if b:
            asc = "".join(chr(x) if 0x20 <= x < 0x7f else "." for x in b)
            lines.append("%08x  %s  %s" % (off, " ".join("%02x" % x for x in b), asc))
    lines.append("")

    # 4) 手工 ASCII 扫描 0xa7000-0xab000 (避开 idautils.Strings API 变化)
    lines.append("--- strings 0xa7000-0xab000 ---")
    data = ida_bytes.get_bytes(0xA7000, 0x4000)
    if data:
        i = 0
        while i < len(data):
            if 0x20 <= data[i] < 0x7f:
                j = i
                while j < len(data) and 0x20 <= data[j] < 0x7f:
                    j += 1
                if j - i >= 4:
                    lines.append("%08x: %s" % (0xA7000 + i, data[i:j].decode("latin1")))
                i = j
            else:
                i += 1
    else:
        lines.append("get_bytes FAIL")
    lines.append("")

    # 5) 尝试建函数（ret-CFG 会截断，只取前段）
    try:
        r = ida_funcs.add_func(0x28065C)
        lines.append("add_func(0x28065c) -> %s" % r)
    except Exception as e:
        lines.append("add_func fail: %s" % e)

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
