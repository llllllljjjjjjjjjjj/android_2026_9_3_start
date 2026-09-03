# IDA 9.2: dump 0x5CDB28 (x-ss-stub 值计算) + sub_32E6C4
import ida_auto, ida_pro, ida_funcs, idautils, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_5cdb28.json"
FUNCS = [0x5CDB28, 0x32E6C4]

def dump_func(fa, max_insns=4000):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return None
    insns = []
    ea = fn.start_ea
    cnt = 0
    while ea < fn.end_ea and cnt < max_insns:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt; cnt += 1
    strings = {}
    ea = fn.start_ea
    while ea < fn.end_ea:
        m = idc.print_insn_mnem(ea)
        if m in ("ADRP", "ADRL"):
            reg = idc.print_operand(ea, 0)
            if m == "ADRP":
                page = idc.get_operand_value(ea, 1)
                nxt = idc.next_head(ea, fn.end_ea)
                if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "ADD":
                    if idc.print_operand(nxt, 0) == reg and idc.print_operand(nxt, 1) == reg:
                        target = page + idc.get_operand_value(nxt, 2)
                        s = idc.get_strlit_contents(target, -1, 0)
                        if s: strings[hex(target)] = s.decode(errors="ignore")
            else:
                target = idc.get_operand_value(ea, 1)
                s = idc.get_strlit_contents(target, -1, 0)
                if s: strings[hex(target)] = s.decode(errors="ignore")
        nxt = idc.next_head(ea, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt
    callees = []
    ea = fn.start_ea
    while ea < fn.end_ea:
        m = idc.print_insn_mnem(ea)
        if m == "BL":
            t = idc.get_operand_value(ea, 0)
            if t != ida_idaapi.BADADDR:
                callees.append({"from": hex(ea), "to": hex(t)})
        ea = idc.next_head(ea, fn.end_ea + 4)
        if ea == ida_idaapi.BADADDR: break
    return {"addr": hex(fn.start_ea), "end": hex(fn.end_ea), "strings": strings,
            "callees": callees, "insns": insns}

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    for f in FUNCS:
        result["func_" + hex(f)] = dump_func(f)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done")
    ida_pro.qexit(0)

main()
