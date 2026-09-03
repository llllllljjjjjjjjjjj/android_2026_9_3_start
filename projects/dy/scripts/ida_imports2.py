# IDA 9.2: dump 0x5c0000-0x5ce000 import 跳板区 (修复版: 迭代上限 + 超时保护)
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, ida_bytes
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_imports2.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    ea = 0x5c0000
    iter_cnt = 0
    while ea < 0x5ce000 and iter_cnt < 20000:
        iter_cnt += 1
        fn = ida_funcs.get_func(ea)
        if fn and fn.start_ea >= 0x5c0000:
            fstart = fn.start_ea
            insns = []
            e2 = fstart
            cnt = 0
            while e2 < fn.end_ea and cnt < 8:
                insns.append(idc.generate_disasm_line(e2, 0))
                nxt = idc.next_head(e2, fn.end_ea + 4)
                if nxt == ida_idaapi.BADADDR:
                    break
                e2 = nxt
                cnt += 1
            got = None
            e2 = fstart
            inner = 0
            while e2 < fn.end_ea and inner < 100:
                inner += 1
                m = idc.print_insn_mnem(e2)
                if m == "ADRP":
                    page = idc.get_operand_value(e2, 1)
                    nxt = idc.next_head(e2, fn.end_ea)
                    if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "LDR":
                        op1 = idc.print_operand(nxt, 1)
                        if op1 and "#" in op1:
                            tgt = page + idc.get_operand_value(nxt, 1)
                            nm = idc.get_name(tgt)
                            got = {"slot": hex(tgt), "name": nm}
                            break
                nxt2 = idc.next_head(e2, fn.end_ea + 4)
                if nxt2 == ida_idaapi.BADADDR or nxt2 <= e2:
                    break
                e2 = nxt2
            result[hex(fstart)] = {"end": hex(fn.end_ea), "insns": insns, "got": got}
            ea = fn.end_ea
        else:
            ea += 4
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("trampolines:", len(result), "iter:", iter_cnt)
    ida_pro.qexit(0)

try:
    main()
except Exception as e:
    print("ERR:", e)
    ida_pro.qexit(1)
