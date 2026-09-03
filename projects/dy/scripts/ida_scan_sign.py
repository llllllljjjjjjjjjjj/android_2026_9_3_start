# IDA 9.2 headless scan v2: sign strings xrefs + RegisterNatives table extraction
import ida_auto
import ida_pro
import ida_funcs
import ida_name
import ida_bytes
import ida_idaapi
import idautils
import idc
import json
import sys

OUT = idc.ARGV[0] if len(idc.ARGV) > 0 else r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_scan.json"

TARGETS = [
    "x-metasec-bypass-ttnet-features", "Tt-Forbid-Reuse",
    "x-gorgon", "x-ladon", "x-soter", "x-argus", "x-helios",
    "x-khronos", "x-medusa", "x-perseus", "x-typhon", "x-bogus",
]


def walk_back_for_regs(start_ea, end_ea):
    """walk back from BLR site up to 0x400 bytes, find ADRP+ADD for X2 and MOV for W3"""
    regs = {"x2": None, "x3": None, "x1": None}
    ea = start_ea
    limit = max(end_ea, start_ea - 0x400)
    adrp = {}
    while ea >= limit:
        m = idc.print_insn_mnem(ea)
        if m == "ADRP":
            r = idc.print_operand(ea, 0)
            val = idc.get_operand_value(ea, 1)
            adrp[r] = val
        elif m == "ADD":
            r = idc.print_operand(ea, 0)
            # ADD X2, XN, #imm  (Xn may be the ADRP reg)
            src = idc.print_operand(ea, 1)
            if r == "X2" and src in adrp and regs["x2"] is None:
                regs["x2"] = adrp[src] + idc.get_operand_value(ea, 2)
            if r == "X1" and src in adrp and regs["x1"] is None:
                regs["x1"] = adrp[src] + idc.get_operand_value(ea, 2)
        elif m == "ADR":
            r = idc.print_operand(ea, 0)
            if r == "X2" and regs["x2"] is None:
                regs["x2"] = idc.get_operand_value(ea, 1)
            if r == "X1" and regs["x1"] is None:
                regs["x1"] = idc.get_operand_value(ea, 1)
        elif m == "MOV":
            r = idc.print_operand(ea, 0)
            if r in ("W3", "X3") and regs["x3"] is None:
                regs["x3"] = idc.get_operand_value(ea, 1)
            if r == "W1" and regs["x1"] is None:
                regs["x1"] = idc.get_operand_value(ea, 1)
        ea = idc.prev_head(ea, limit)
    return regs


def dump_method_table(base, n):
    table = []
    if base is None or not n or n > 4096:
        return table
    for i in range(n):
        entry = base + i * 24
        vals = [ida_bytes.get_qword(entry + 8 * k) for k in range(3)]
        if all(vals):
            nm = idc.get_strlit_contents(vals[0])
            sg = idc.get_strlit_contents(vals[1])
            table.append({
                "name": nm.decode() if nm else None,
                "sig": sg.decode() if sg else None,
                "fn": hex(vals[2]),
            })
    return table


def main():
    ida_auto.auto_wait()
    result = {"file": idc.get_input_file_path(),
              "strings": {}, "register_natives": []}

    # ---- 1. string xrefs ----
    str_items = []
    for s in idautils.Strings():
        try:
            txt = str(s)
        except Exception:
            continue
        for t in TARGETS:
            if t.lower() in txt.lower():
                str_items.append((s.ea, txt))
                break
    for ea, txt in str_items:
        xrefs = []
        for xr in idautils.XrefsTo(ea):
            fn = ida_funcs.get_func(xr.frm)
            xrefs.append({
                "from": hex(xr.frm),
                "func": hex(fn.start_ea) if fn else None,
                "func_end": hex(fn.end_ea) if fn else None,
            })
        result["strings"][hex(ea)] = {"text": txt, "xrefs": xrefs}

    # ---- 2. RegisterNatives: scan whole .text for LDR xN,[xM,#imm8*8] + BLR xN ----
    # JNI RegisterNatives is index 215 -> offset 0x6B8; also accept 0x458 (older tables)
    text = ida_name.get_name_ea(ida_idaapi.BADADDR, ".text")
    if text == ida_idaapi.BADADDR:
        text = ida_idaapi.BADADDR
        segs = idautils.Segments()
        for s in segs:
            if idc.get_segm_name(s) == ".text":
                text = s
                break
    if text != ida_idaapi.BADADDR:
        seg_end = idc.get_segm_end(text)
        ea = text
        hits = {}
        while ea < seg_end and ea != ida_idaapi.BADADDR:
            m = idc.print_insn_mnem(ea)
            if m == "LDR":
                op1 = idc.print_operand(ea, 1)
                # match [xN, #0x458] or [xN, #0x6B8]
                for off in ("#0x458", "#0x6B8"):
                    if off in op1:
                        dst = idc.print_operand(ea, 0)
                        # next BLR dst within 0x40
                        scan = ea
                        limit = ea + 0x40
                        while scan < limit:
                            if idc.print_insn_mnem(scan) == "BLR" and idc.print_operand(scan, 0) == dst:
                                hits[hex(ea)] = (ea, scan)
                                break
                            scan = idc.next_head(scan, limit)
                        break
            ea = idc.next_head(ea, seg_end)
        for ldr_ea, blr_ea in hits.values():
            fn = ida_funcs.get_func(ldr_ea)
            regs = walk_back_for_regs(ldr_ea, fn.start_ea if fn else ldr_ea - 0x400)
            entry = {
                "ldr_ea": hex(ldr_ea), "blr_ea": hex(blr_ea),
                "func": hex(fn.start_ea) if fn else None,
                "methods_ptr": hex(regs["x2"]) if regs["x2"] is not None else None,
                "count": regs["x3"],
            }
            entry["table"] = dump_method_table(regs["x2"], regs["x3"])
            if entry["table"]:
                result["register_natives"].append(entry)

    # ---- 3. JNI_OnLoad ----
    jni_onload = ida_name.get_name_ea(ida_idaapi.BADADDR, "JNI_OnLoad")
    if jni_onload != ida_idaapi.BADADDR:
        result["jni_onload"] = hex(jni_onload)
        fn = ida_funcs.get_func(jni_onload)
        if fn:
            result["jni_onload_func"] = {"start": hex(fn.start_ea), "end": hex(fn.end_ea)}
            # dump disasm listing of JNI_OnLoad (first 300 insns)
            ins = []
            ea = fn.start_ea
            cnt = 0
            while ea < fn.end_ea and cnt < 300:
                ins.append(f"{ea:#x}: {idc.generate_disasm_line(ea, 0)}")
                ea = idc.next_head(ea, fn.end_ea)
                cnt += 1
            result["jni_onload_disasm"] = ins

    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    ida_pro.qexit(0)


main()
