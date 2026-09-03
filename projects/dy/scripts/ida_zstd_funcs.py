# IDA 9.2: dump ttnet_zstd 组件关键函数（解压 + 字典加载定位）
import ida_auto, ida_pro, ida_funcs, idc, idautils, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\artifacts\zstd_funcs.json"
FUNCS = [0x49a060, 0x49bb9c, 0x49a720, 0x49e054, 0x339c84, 0x49dfa0]

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
                        refs[hex(target)] = s.decode(errors="ignore")
        elif m in ("ADR", "ADRL"):
            target = idc.get_operand_value(ea, 1)
            s = idc.get_strlit_contents(target, -1, 0)
            if s:
                refs[hex(target)] = s.decode(errors="ignore")
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
                out.append((ea, t))
        ea = idc.next_head(ea, ea_end)
    return out

def dump_func(fa, max_insns=3000):
    fn = ida_funcs.get_func(fa)
    if not fn:
        return {"addr": hex(fa), "error": "no func"}
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
    return {
        "addr": hex(fn.start_ea), "end": hex(fn.end_ea),
        "size": fn.end_ea - fn.start_ea,
        "strings": collect_strings_refd(fn.start_ea, fn.end_ea),
        "callees": [{"from": hex(f), "to": t} for f, t in collect_callees(fn.start_ea, fn.end_ea)],
        "insns": insns,
    }

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    result = {"funcs": {}}
    for f in FUNCS:
        rec = dump_func(f)
        result["funcs"][hex(f)] = rec
        print(hex(f), "->", rec.get("addr"), "~", rec.get("end"), "size", rec.get("size"),
              "| strings:", list(rec.get("strings", {}).values())[:5])
        # 打印 callee 目标（找解压/字典函数）
        for c in rec.get("callees", []):
            cf = ida_funcs.get_func(c["to"])
            if cf:
                print("    BL ->", hex(c["to"]), "(func", hex(cf.start_ea), ")")
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("saved", OUT)
    ida_pro.qexit(0)

main()
