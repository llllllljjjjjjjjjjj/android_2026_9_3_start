# IDA 9.2: 批量 dump API 表槽位函数 (FrontierParams 簇 + 0x26xxxx 族 + stub 验证)
# 目标: 找神头生成器候选 (参数模式/加密原语引用)
import ida_auto, ida_pro, ida_funcs, idautils, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_frontier.json"

# 槽位函数清单 (从 ida_5d5_code.json + ida_api_table.json 提取)
FUNCS = [
    # stub 验证
    0x1EE748, 0x1EE760, 0x1F2CA8,
    # FrontierParams 簇 (0x5d4f20-0x5d4fb0)
    0x25C210, 0x25C2D4, 0x25C2C8, 0x25C2FC, 0x25C310, 0x25C3C4, 0x25C3B8,
    0x25C3EC, 0x25C400, 0x25C4A8, 0x25B170, 0x25C4D0, 0x25C4E4, 0x25C5FC,
    0x25C5F0, 0x25C624, 0x25C638, 0x25C7C8, 0x25C7BC, 0x25C86C, 0x25C880,
    0x25C8AC, 0x25C920, 0x25CD28, 0x25CE14, 0x25E464, 0x25E428,
    # 0x26xxxx 族 (表后半)
    0x26D190, 0x26C440, 0x26C938, 0x26B4C8, 0x26CA6C, 0x26CAA4, 0x26B688,
    0x26B6E4, 0x26B7F0, 0x26B820, 0x26B87C, 0x26BA08, 0x26BA6C, 0x26BA14,
    0x26D220, 0x26D234, 0x26D304, 0x26FB58, 0x26FBF8, 0x26FC80, 0x26FC90,
    0x26D33C, 0x26D850, 0x26DB5C, 0x26DC58, 0x26E150, 0x26E284, 0x26BA78,
    0x26BD84, 0x26E298, 0x26E718, 0x26E724, 0x26E8F0, 0x26E968, 0x26EAE8,
    0x26EC94, 0x26FFFC, 0x26F9F4, 0x26F128, 0x26F5C8, 0x26F744, 0x26FA40,
]

def dump_func(fa, max_insns=25):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return {"error": "no func"}
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
                callees.append({"from": hex(ea), "to": hex(t),
                                "name": idc.get_name(t) or ""})
        ea = idc.next_head(ea, fn.end_ea + 4)
        if ea == ida_idaapi.BADADDR: break
    # 调用者 (xref)
    callers = []
    for xr in idautils.XrefsTo(fn.start_ea, 0):
        ff = ida_funcs.get_func(xr.frm)
        callers.append({"from": hex(xr.frm),
                        "func": hex(ff.start_ea) if ff else None})
    return {"addr": hex(fn.start_ea), "end": hex(fn.end_ea),
            "size": fn.end_ea - fn.start_ea,
            "strings": strings, "callees": callees,
            "callers": callers, "insns": insns}

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    for f in FUNCS:
        result["func_" + hex(f)] = dump_func(f)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done", len(result))
    ida_pro.qexit(0)

main()
