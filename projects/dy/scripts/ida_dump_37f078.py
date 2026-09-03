# IDA 9.2: dump function disassembly + callees + referenced strings
import ida_auto, ida_pro, ida_funcs, ida_bytes, ida_idaapi, idautils, idc
import json, sys

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_func_37f078.json"
FUNCS = [0x37f078]
DEPTH = 0
RANGE_START = 0x37f078
RANGE_END = 0x37f200

def collect_strings_refd(ea_start, ea_end):
    """strings referenced via ADRP+ADD or ADR within the function body"""
    refs = {}
    ea = ea_start
    while ea < ea_end:
        m = idc.print_insn_mnem(ea)
        if m == "ADRP":
            reg = idc.print_operand(ea, 0)
            page = idc.get_operand_value(ea, 1)
            # look ahead for ADD reg, reg, #imm
            nxt = idc.next_head(ea, ea_end)
            if nxt != ida_idaapi.BADADDR and idc.print_insn_mnem(nxt) == "ADD":
                if idc.print_operand(nxt, 0) == reg and idc.print_operand(nxt, 1) == reg:
                    target = page + idc.get_operand_value(nxt, 2)
                    s = idc.get_strlit_contents(target, -1, 0)
                    if s:
                        refs[hex(target)] = s.decode()
        elif m == "ADR":
            target = idc.get_operand_value(ea, 1)
            s = idc.get_strlit_contents(target, -1, 0)
            if s:
                refs[hex(target)] = s.decode()
        ea = idc.next_head(ea, ea_end)
    return refs

def collect_callees(ea_start, ea_end):
    """BL/BLR targets (direct and via literal pool)"""
    out = []
    ea = ea_start
    while ea < ea_end:
        m = idc.print_insn_mnem(ea)
        if m == "BL":
            t = idc.get_operand_value(ea, 0)
            if t != ida_idaapi.BADADDR:
                out.append((ea, t, "BL"))
        elif m in ("BLR", "BR"):
            # may be indirect via xN loaded from literal pool; try operand value
            t = idc.get_operand_value(ea, 0)
            if t not in (None, -1, ida_idaapi.BADADDR, 0):
                out.append((ea, t, m))
        ea = idc.next_head(ea, ea_end)
    return out

def dump_func(fa, depth):
    if depth < 0:
        return None
    fn = ida_funcs.get_func(fa)
    if not fn:
        return {"addr": hex(fa), "error": "no func"}
    insns = []
    ea = fn.start_ea
    cnt = 0
    while ea < fn.end_ea and cnt < 4000:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR:
            break
        ea = nxt
        cnt += 1
    rec = {
        "addr": hex(fn.start_ea), "end": hex(fn.end_ea),
        "strings": collect_strings_refd(fn.start_ea, fn.end_ea),
        "callees": [{"from": hex(f), "to": hex(t), "type": ty}
                    for f, t, ty in collect_callees(fn.start_ea, fn.end_ea)],
        "insns": insns,
        "range_insns": [],
    }
    # focused range disasm
    ea = RANGE_START
    while ea < RANGE_END:
        rec["range_insns"].append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, RANGE_END + 4)
        if nxt == ida_idaapi.BADADDR:
            break
        ea = nxt
    if depth > 0:
        rec["callee_detail"] = {hex(t): dump_func(t, depth - 1)
                                for _, t, ty in rec["callees"]
                                if ty == "BL" and ida_funcs.get_func(t)}
    return rec

def main():
    ida_auto.auto_wait()
    result = {"file": idc.get_input_file_path(),
              "funcs": {hex(f): dump_func(f, DEPTH) for f in FUNCS}}
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    ida_pro.qexit(0)

main()
