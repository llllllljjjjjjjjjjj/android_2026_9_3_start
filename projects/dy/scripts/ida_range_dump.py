# IDA 9.2: dump 指定地址范围反汇编 (JNI_OnLoad 第二段 0x27e8a0 起)
import ida_auto, ida_pro, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_jni_seg2.json"
START = 0x27e8a0
END = 0x27f200

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    insns = []
    ea = START
    while ea < END:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, END + 4)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt
        if len(insns) > 6000: break
    # 也收集该范围的 ADRP 字符串引用
    strings = {}
    ea = START
    while ea < END:
        m = idc.print_insn_mnem(ea)
        if m == "ADRP":
            reg = idc.print_operand(ea, 0)
            page = idc.get_operand_value(ea, 1)
            nxt = idc.next_head(ea, END)
            if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "ADD":
                if idc.print_operand(nxt, 0) == reg and idc.print_operand(nxt, 1) == reg:
                    target = page + idc.get_operand_value(nxt, 2)
                    s = idc.get_strlit_contents(target, -1, 0)
                    if s:
                        strings[hex(target)] = s.decode()
        nxt = idc.next_head(ea, END + 4)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt
    with open(OUT, "w") as f:
        json.dump({"range": [hex(START), hex(END)], "strings": strings, "insns": insns}, f, indent=1)
    print("insns:", len(insns), "strings:", len(strings))
    ida_pro.qexit(0)

main()
