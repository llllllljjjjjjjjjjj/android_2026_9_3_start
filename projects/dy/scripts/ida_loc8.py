# IDA 9.2: 定位 hook 抓到的调用者地址所在函数 (2f1ed8/2f1f6c/269240/47dce8/273394/416bc8/21b628)
# + dump 0x229d24 (0x5d4f00 槽位函数)
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_loc8.json"
LOCS = [0x2f1ed8, 0x2f1f6c, 0x269240, 0x47dce8, 0x273394, 0x416bc8, 0x21b628, 0x229d24, 0x37f460]

def dump_func(fa, max_insns=60):
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
    # BL callees
    callees = []
    ea = fn.start_ea
    while ea < fn.end_ea:
        m = idc.print_insn_mnem(ea)
        if m == "BL":
            t = idc.get_operand_value(ea, 0)
            if t != ida_idaapi.BADADDR:
                callees.append({"from": hex(ea), "to": hex(t), "name": idc.get_name(t) or ""})
        ea = idc.next_head(ea, fn.end_ea + 4)
        if ea == ida_idaapi.BADADDR: break
    # callers
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
    for l in LOCS:
        fn = ida_funcs.get_func(l)
        if not fn:
            result["loc_" + hex(l)] = None
            continue
        result["loc_" + hex(l) + "_in_" + hex(fn.start_ea)] = {
            "offset_in_func": l - fn.start_ea}
    # 全量 dump 这些函数
    seen = set()
    for l in LOCS:
        fn = ida_funcs.get_func(l)
        if fn and fn.start_ea not in seen:
            seen.add(fn.start_ea)
            result["func_" + hex(fn.start_ea)] = dump_func(fn.start_ea)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done", len(result))
    ida_pro.qexit(0)

try:
    main()
except Exception as e:
    print("ERR:", e)
    ida_pro.qexit(1)
