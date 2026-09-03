# IDA 9.2: dump ttnet CertVerify 相关导出函数（签名/结构体布局/内部调用者）
import ida_auto, ida_pro, ida_funcs, idc, ida_idaapi, idautils
import time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_certverify.txt"

TARGETS = [
    "Cronet_CertVerify_CreateWith",
    "Cronet_CertVerify_Create",
    "Cronet_CertVerify_DoVerifyV2",
    "Cronet_Engine_SetMockCertVerifierForTesting",
    "Cronet_EngineParams_enable_public_key_pinning_bypass_for_local_trust_anchors_set",
    "Cronet_EngineParams_public_key_pins_add",
    "Cronet_VerifyResult_Create",
    "Cronet_VerifyParamsV2_Create",
]

CALLER_OF = [
    "Cronet_CertVerify_DoVerifyV2",
    "Cronet_Engine_SetMockCertVerifierForTesting",
    "Cronet_EngineParams_public_key_pins_add",
]


def dump_range(start, end, lines, maxcnt=400, indent="  "):
    e, cnt = start, 0
    while e < end and e != ida_idaapi.BADADDR and cnt < maxcnt:
        dis = idc.generate_disasm_line(e, 0)
        cmt = idc.get_cmt(e, 0)
        line = "%s%08x  %s" % (indent, e, dis)
        if cmt:
            line += "  ; " + cmt
        lines.append(line)
        nxt = idc.next_head(e, end + 4)
        if nxt == ida_idaapi.BADADDR or nxt <= e:
            break
        e = nxt
        cnt += 1


def dump_func(name, lines, maxcnt=400):
    ea = idc.get_name_ea_simple(name)
    lines.append("=" * 70)
    if ea == ida_idaapi.BADADDR:
        lines.append("%s: NOT FOUND" % name)
        return
    lines.append("%s @ %s" % (name, hex(ea)))
    fn = ida_funcs.get_func(ea)
    if not fn:
        lines.append("  (no func at %s, raw dump 40)" % hex(ea))
        dump_range(ea, ea + 0x200, lines, 40)
        return
    lines.append("  func: %s - %s size=0x%x" % (hex(fn.start_ea), hex(fn.end_ea), fn.end_ea - fn.start_ea))
    dump_range(fn.start_ea, fn.end_ea, lines, maxcnt)


def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 300:
        time.sleep(2)
    lines = []
    for n in TARGETS:
        dump_func(n, lines)

    # 关键: DoVerifyV2 / SetMockCertVerifier / public_key_pins_add 的调用者 = 校验实现本体
    for n in CALLER_OF:
        lines.append("=" * 70)
        ea = idc.get_name_ea_simple(n)
        if ea == ida_idaapi.BADADDR:
            lines.append("%s: NOT FOUND" % n)
            continue
        lines.append("callers of %s (%s):" % (n, hex(ea)))
        seen = set()
        for x in idautils.XrefsTo(ea):
            if x.frm in seen:
                continue
            seen.add(x.frm)
            f = ida_funcs.get_func(x.frm)
            if not f:
                lines.append("  call from %08x (no func)" % x.frm)
                dump_range(x.frm, x.frm + 0x80, lines, 20, "      ")
            else:
                fname = idc.get_func_name(f.start_ea)
                lines.append("  caller func %08x - %08x (%s), call at %08x" %
                             (f.start_ea, f.end_ea, fname, x.frm))
                dump_range(f.start_ea, f.end_ea, lines, 400)

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print("wrote", OUT, "lines", len(lines))
    ida_pro.qexit(0)


main()
