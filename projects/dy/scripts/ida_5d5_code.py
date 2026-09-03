import ida_auto, ida_pro, idc, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_5d5_code.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    insns = []
    ea = 0x5d4f00
    while ea < 0x5d5600:
        insns.append({"ea": hex(ea), "dis": idc.generate_disasm_line(ea, 0)})
        nxt = idc.next_head(ea, 0x5d5604)
        if nxt == ida_idaapi.BADADDR: break
        ea = nxt
    with open(OUT, "w") as f:
        json.dump({"insns": insns}, f, indent=1)
    print("insns:", len(insns))
    ida_pro.qexit(0)

main()
