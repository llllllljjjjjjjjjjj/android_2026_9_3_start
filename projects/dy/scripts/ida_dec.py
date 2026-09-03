# IDA 9.2: 分析已解密 libmetasec_ml_dec.so 的 0x28065c (enable_auto(False) 防内存爆炸)
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_metasec_dec.txt"

def main():
    try:
        ida_auto.enable_auto(False)
        print("auto analysis disabled")
    except Exception as e:
        print("enable_auto fail:", e)
    time.sleep(8)
    lines = []
    # 1) 反汇编 0x28065c 起 0x800 字节
    lines.append("--- disasm 0x28065c + 0x800 ---")
    e = 0x28065c
    cnt = 0
    while e < 0x28065c + 0x800 and cnt < 800:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%08x  %s" % (e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, 0x28065c + 0x800 + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1
    # 2) 字符串 (0xa7000-0xab000 区域, 入口 adrp 引用的)
    lines.append("")
    lines.append("--- strings 0xa7000-0xab000 ---")
    try:
        for s in idautils.Strings(0xa7000, 0xab000):
            if len(str(s)) > 2:
                lines.append("%08x: %s" % (s.ea, str(s)))
    except Exception as ex:
        lines.append("strings ERR " + str(ex))
    # 3) 全局区 0x3e5f80-0x3e6200 hex dump
    lines.append("")
    lines.append("--- globals 0x3e5f80-0x3e6200 ---")
    try:
        for off in range(0x3e5f80, 0x3e6200, 16):
            b = idc.get_bytes(off, 16)
            if b:
                hexs = " ".join("%02x" % x for x in b)
                lines.append("%08x  %s" % (off, hexs))
    except Exception as ex:
        lines.append("globals ERR " + str(ex))
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, len(lines))
    ida_pro.qexit(0)

try:
    main()
except Exception as ex:
    print("ERR:", ex)
    ida_pro.qexit(1)
