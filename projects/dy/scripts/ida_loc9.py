# IDA 9.2: 补全 416990 后段 + 2732ac 全量 + 412110 所在函数 + 416bc8 上下文
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_loc9.json"

def dump_range(start, end, label, max_insns=200):
    insns = []
    ea = start
    cnt = 0
    while ea < end and cnt < max_insns:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, end + 4)
        if nxt == ida_idaapi.BADADDR:
            break
        ea = nxt
        cnt += 1
    return {label: insns}

def dump_func(fa, max_insns=200):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return None
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
    callers = []
    for xr in idautils.XrefsTo(fn.start_ea, 0):
        ff = ida_funcs.get_func(xr.frm)
        callers.append({"from": hex(xr.frm), "func": hex(ff.start_ea) if ff else None})
    return {"addr": hex(fn.start_ea), "end": hex(fn.end_ea), "size": fn.end_ea - fn.start_ea,
            "insns": insns, "callees": callees, "callers": callers}

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    # 1) 416990 全量
    result["func_0x416990_full"] = dump_func(0x416990)
    # 2) 2732ac 全量
    result["func_0x2732ac_full"] = dump_func(0x2732ac)
    # 3) 412110 所在函数 (调 416990 的调用者之一)
    result["func_at_0x412110"] = dump_func(0x412110)
    # 4) 4184d8 所在函数
    result["func_at_0x4184d8"] = dump_func(0x4184d8)
    # 5) 435a0c 所在函数
    result["func_at_0x435a0c"] = dump_func(0x435a0c)
    # 6) 2039e4 所在函数 (21b57c 调用者)
    result["func_at_0x2039e4"] = dump_func(0x2039e4)
    # 7) 416bc8 上下文 +-24 指令
    fn = ida_funcs.get_func(0x416bc8)
    if fn:
        # 往前找 24 条指令的起点
        ea = 0x416bc8
        for i in range(24):
            p = idc.prev_head(ea, fn.start_ea)
            if p == ida_idaapi.BADADDR:
                break
            ea = p
        result["ctx_416bc8"] = dump_range(ea, min(fn.end_ea, 0x416bc8 + 4*40), "ctx_416bc8")
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done", len(result))
    ida_pro.qexit(0)

try:
    main()
except Exception as e:
    print("ERR:", e)
    ida_pro.qexit(1)
