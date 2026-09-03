# IDA 9.2: dump 0x5c0000-0x5ce000 import 跳板区, 解析每个跳板的 GOT 目标符号
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, ida_bytes
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_imports.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    ea = 0x5c0000
    while ea < 0x5ce000:
        fn = ida_funcs.get_func(ea)
        if fn:
            fstart = fn.start_ea
            if fstart >= 0x5c0000:
                insns = []
                e2 = fstart
                cnt = 0
                while e2 < fn.end_ea and cnt < 6:
                    insns.append(idc.generate_disasm_line(e2, 0))
                    e2 = idc.next_head(e2, fn.end_ea + 4)
                    cnt += 1
                # 找 GOT 目标: ADRP X16, off_X 模式
                got = None
                e2 = fstart
                while e2 < fn.end_ea:
                    if idc.print_insn_mnem(e2) == "ADRP":
                        page = idc.get_operand_value(e2, 1)
                        # 下一指令 LDR X17, [X16, #off] -> target = page + off
                        nxt = idc.next_head(e2, fn.end_ea)
                        if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "LDR":
                            if idc.print_operand(nxt, 1) and "#" in idc.print_operand(nxt, 1):
                                tgt = page + idc.get_operand_value(nxt, 1)
                                nm = idc.get_name(tgt)
                                got = {"slot": hex(tgt), "name": nm}
                                break
                    e2 = idc.next_head(e2, fn.end_ea + 4)
                    if e2 == ida_idaapi.BADADDR: break
                if fstart not in result or got:
                    result[hex(fstart)] = {"insns": insns, "got": got}
            ea = fn.end_ea
        else:
            ea += 4
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("trampolines:", len(result))
    ida_pro.qexit(0)

main()
