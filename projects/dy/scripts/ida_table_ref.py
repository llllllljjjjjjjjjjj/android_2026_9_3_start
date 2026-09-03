# IDA 9.2: 查 0x5d5400 表基址的所有引用 + sscronet 导出符号
import ida_auto, ida_pro, idc, ida_idaapi, idautils, ida_funcs, ida_entry
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_table_ref.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {"refs_to_5d5400": [], "exports": []}
    for xr in idautils.XrefsTo(0x5d5400, 0):
        f = ida_funcs.get_func(xr.frm)
        result["refs_to_5d5400"].append({"from": hex(xr.frm), "func": hex(f.start_ea) if f else None})
    # 表基址+偏移引用 (ADRP 引 5d5xxx 页的)
    for xr in idautils.XrefsTo(0x5d5000, 0):
        f = ida_funcs.get_func(xr.frm)
        result["refs_to_5d5000"].append({"from": hex(xr.frm), "func": hex(f.start_ea) if f else None})
    # 导出符号
    n = ida_entry.get_entry_qty()
    for i in range(n):
        ea = ida_entry.get_entry(ida_entry.get_entry_ordinal(i))
        nm = idc.get_name(ea)
        result["exports"].append({"ea": hex(ea), "name": nm})
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("refs:", len(result["refs_to_5d5400"]), "| exports:", len(result["exports"]))
    ida_pro.qexit(0)

main()
