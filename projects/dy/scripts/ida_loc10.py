# IDA 9.2: dump 3411B4 所在函数 (神头写入者!) + 411e74 所在函数 + 412680 全量
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_loc10.json"

def dump_func(fa, max_insns=400):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return {"error": "no func at " + hex(fa)}
    insns = []
    ea = fn.start_ea
    cnt = 0
    while ea < fn.end_ea and cnt < max_insns:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR:
            break
        ea = nxt
        cnt += 1
    callees = []
    ea = fn.start_ea
    while ea < fn.end_ea:
        m = idc.print_insn_mnem(ea)
        if m in ("BL", "BLR"):
            t = idc.get_operand_value(ea, 0)
            if t != ida_idaapi.BADADDR:
                callees.append({"from": hex(ea), "to": hex(t), "name": idc.get_name(t) or ""})
        ea = idc.next_head(ea, fn.end_ea + 4)
        if ea == ida_idaapi.BADADDR:
            break
    strings = {}
    ea = fn.start_ea
    while ea < fn.end_ea:
        m = idc.print_insn_mnem(ea)
        if m == "ADRP":
            reg = idc.print_operand(ea, 0)
            page = idc.get_operand_value(ea, 1)
            nxt = idc.next_head(ea, fn.end_ea)
            if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "ADD":
                if idc.print_operand(nxt, 0) == reg and idc.print_operand(nxt, 1) == reg:
                    target = page + idc.get_operand_value(nxt, 2)
                    s = idc.get_strlit_contents(target, -1, 0)
                    if s:
                        strings[hex(target)] = s.decode(errors="ignore")
        ea = idc.next_head(ea, fn.end_ea + 4)
        if ea == ida_idaapi.BADADDR:
            break
    callers = []
    for xr in idautils.XrefsTo(fn.start_ea, 0):
        ff = ida_funcs.get_func(xr.frm)
        callers.append({"from": hex(xr.frm), "func": hex(ff.start_ea) if ff else None})
    return {"addr": hex(fn.start_ea), "end": hex(fn.end_ea), "size": fn.end_ea - fn.start_ea,
            "insns": insns, "callees": callees, "callers": callers, "strings": strings}

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    # 3411B4 = 神头写入者候选 (411e74 BL 它, 412680 由它调用)
    result["func_at_0x3411b4"] = dump_func(0x3411B4)
    # 411e74 所在函数
    result["func_at_0x411e74"] = dump_func(0x411E74)
    # 412680 全量 (MaybeStartTransactionInternal)
    result["func_0x412680"] = dump_func(0x412680)
    # 411c90 是什么 (BT 帧)
    result["func_at_0x411c90"] = dump_func(0x411C90)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done", len(result))
    ida_pro.qexit(0)

try:
    main()
except Exception as e:
    print("ERR:", e)
    ida_pro.qexit(1)
