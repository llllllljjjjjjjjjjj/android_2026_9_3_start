# 快速版: 只分析 JNI_OnLoad@0x27e7f0, 找 RegisterNatives 方法表 (不限时等全量分析)
import ida_auto, ida_pro, ida_funcs, ida_name, idautils, idc, ida_idaapi
import json, time, sys

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\metasec_jni.json"
JNI = 0x27e7f0

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 90:
        time.sleep(2)
    result = {"jni_onload": hex(JNI), "insns": [], "register_natives": [], "jni_table": []}
    fn = ida_funcs.get_func(JNI)
    if fn:
        ea = fn.start_ea
        cnt = 0
        while ea < fn.end_ea and cnt < 4000:
            dis = idc.generate_disasm_line(ea, 0)
            result["insns"].append({"ea": hex(ea), "dis": dis})
            nxt = idc.next_head(ea, fn.end_ea + 4)
            if nxt == ida_idaapi.BADADDR: break
            ea = nxt; cnt += 1
    # 找 LDR xN,[xM,#imm] + BLR xN 模式 (RegisterNatives 特征, 偏移含 0x6B8)
    seg = idc.get_segm_by_sel(idc.selector_by_name(".text"))
    if seg:
        start, end = idc.get_segm_start(seg), idc.get_segm_end(seg)
        # 只在 JNI_OnLoad 函数范围内找
        if fn:
            start, end = fn.start_ea, fn.end_ea
        ea = start
        while ea < end:
            m = idc.print_insn_mnem(ea)
            if m == "LDR":
                op1 = idc.print_operand(ea, 1)
                for off in ("#0x6B8", "#0x458", "#0x398"):
                    if off in op1:
                        dst = idc.print_operand(ea, 0)
                        scan = ea; limit = ea + 0x60
                        found = None
                        while scan < limit:
                            if idc.print_insn_mnem(scan) == "BLR" and idc.print_operand(scan, 0) == dst:
                                found = scan; break
                            scan = idc.next_head(scan, limit)
                        if found:
                            # 回追 ADRP+ADD 拿 x0(类名)/x2(方法表)
                            regs = {}
                            w = ea; lim = ea - 0x500
                            while w >= lim:
                                wm = idc.print_insn_mnem(w)
                                if wm == "ADRP":
                                    r = idc.print_operand(w, 0); regs[r] = idc.get_operand_value(w, 1)
                                elif wm == "ADD":
                                    r = idc.print_operand(w, 0); src = idc.print_operand(w, 1)
                                    if src in regs and r in ("X0", "X1", "X2", "X3"):
                                        regs[r + "_addr"] = regs[src] + idc.get_operand_value(w, 2)
                                w = idc.prev_head(w, lim)
                            cls = regs.get("X1_addr")
                            tbl = regs.get("X2_addr")
                            cls_str = idc.get_strlit_contents(cls, -1, 0) if cls else None
                            entry = {"ldr": hex(ea), "blr": hex(found),
                                     "class": cls_str.decode() if cls_str else None,
                                     "class_addr": hex(cls) if cls else None,
                                     "table": hex(tbl) if tbl else None}
                            # dump 方法表: {name_ptr, sig_ptr, fn_ptr} 每 24 字节, 直到 name 为空
                            if tbl:
                                t = tbl; n = 0; methods = []
                                while n < 64:
                                    np = idc.get_qword(t); sp = idc.get_qword(t + 8); fp = idc.get_qword(t + 16)
                                    if np == 0 or sp == 0 or fp == 0: break
                                    nm = idc.get_strlit_contents(np, -1, 0)
                                    sg = idc.get_strlit_contents(sp, -1, 0)
                                    methods.append({"name": nm.decode() if nm else None,
                                                    "sig": sg.decode() if sg else None,
                                                    "fn": hex(fp)})
                                    t += 24; n += 1
                                entry["methods"] = methods
                            result["register_natives"].append(entry)
                        break
            nxt = idc.next_head(ea, end + 4)
            if nxt == ida_idaapi.BADADDR: break
            ea = nxt
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("JNI_OnLoad insns:", len(result["insns"]), "RN sites:", len(result["register_natives"]))
    ida_pro.qexit(0)

main()
