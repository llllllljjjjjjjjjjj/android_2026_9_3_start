# IDA 9.2: dump x-ss-stub 生成函数 (0x26d294 所在函数) + EraseFrom(37F078) 全部调用者
import ida_auto, ida_pro, ida_funcs, idautils, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_ssstub_gen.json"

def dump_func(fa, max_insns=3000):
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
    # strings refd
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
    result["ssstub_gen_func"] = dump_func(0x26d294)
    # EraseFrom 37F078 调用者
    xrefs = []
    for xr in idautils.XrefsTo(0x37F078, 0):
        xrefs.append({"from": hex(xr.frm), "func": hex(ida_funcs.get_func(xr.frm).start_ea) if ida_funcs.get_func(xr.frm) else None})
    result["erasefrom_callers"] = xrefs
    # FindHeader 37ECF0 调用者
    xrefs2 = []
    for xr in idautils.XrefsTo(0x37ECF0, 0):
        xrefs2.append({"from": hex(xr.frm), "func": hex(ida_funcs.get_func(xr.frm).start_ea) if ida_funcs.get_func(xr.frm) else None})
    result["findheader_callers"] = xrefs2
    # SetHeader 37ED64 调用者
    xrefs3 = []
    for xr in idautils.XrefsTo(0x37ED64, 0):
        xrefs3.append({"from": hex(xr.frm), "func": hex(ida_funcs.get_func(xr.frm).start_ea) if ida_funcs.get_func(xr.frm) else None})
    result["setheader_callers"] = xrefs3
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("ssstub func:", result["ssstub_gen_func"]["addr"] if result["ssstub_gen_func"] else None,
          "| EraseFrom callers:", len(xrefs), "| FindHeader callers:", len(xrefs2), "| SetHeader callers:", len(xrefs3))
    ida_pro.qexit(0)

main()
