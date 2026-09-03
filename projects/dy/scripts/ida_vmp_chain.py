# IDA 9.2: dump VMP 跳板链 sub_27E874 + sub_168820 (JNI_OnLoad 尾部分发)
# 限时 60s auto_wait, 只 dump 这两个函数 + 各自 callee 一层
import ida_auto, ida_pro, ida_funcs, ida_name, idautils, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_vmp_chain.json"
FUNCS = [0x27E874, 0x168820]

def collect_strings_refd(ea_start, ea_end):
    refs = {}
    ea = ea_start
    while ea < ea_end:
        m = idc.print_insn_mnem(ea)
        if m == "ADRP":
            reg = idc.print_operand(ea, 0)
            page = idc.get_operand_value(ea, 1)
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
    out = []
    ea = ea_start
    while ea < ea_end:
        m = idc.print_insn_mnem(ea)
        if m == "BL":
            t = idc.get_operand_value(ea, 0)
            if t != ida_idaapi.BADADDR:
                out.append((ea, t, "BL"))
        elif m in ("BLR", "BR"):
            t = idc.get_operand_value(ea, 0)
            if t not in (None, -1, ida_idaapi.BADADDR, 0):
                out.append((ea, t, m))
        ea = idc.next_head(ea, ea_end)
    return out

def dump_func(fa, depth):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return {"addr": hex(fa), "error": "no func"}
    insns = []
    ea = fn.start_ea
    cnt = 0
    while ea < fn.end_ea and cnt < 4000:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, fn.end_ea + 4)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt; cnt += 1
    rec = {
        "addr": hex(fn.start_ea), "end": hex(fn.end_ea),
        "strings": collect_strings_refd(fn.start_ea, fn.end_ea),
        "callees": [{"from": hex(f), "to": hex(t), "type": ty}
                    for f, t, ty in collect_callees(fn.start_ea, fn.end_ea)],
        "insns": insns,
    }
    if depth > 0:
        rec["callee_detail"] = {hex(t): dump_func(t, depth - 1)
                                for _, t, ty in rec["callees"]
                                if ty == "BL" and ida_funcs.get_func(t)}
    return rec

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {"file": idc.get_input_file_path(),
              "funcs": {hex(f): dump_func(f, 1) for f in FUNCS}}
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("dumped", len(result["funcs"]), "funcs")
    ida_pro.qexit(0)

main()
