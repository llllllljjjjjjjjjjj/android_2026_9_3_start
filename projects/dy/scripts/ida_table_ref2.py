import ida_auto, ida_pro, idc, ida_idaapi, idautils, ida_funcs
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_table_ref.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {"refs_to_5d5400": [], "refs_5d5_page": []}
    for xr in idautils.XrefsTo(0x5d5400, 0):
        f = ida_funcs.get_func(xr.frm)
        result["refs_to_5d5400"].append({"from": hex(xr.frm), "func": hex(f.start_ea) if f else None})
    for xr in idautils.XrefsTo(0x5d5000, 0):
        f = ida_funcs.get_func(xr.frm)
        result["refs_5d5_page"].append({"from": hex(xr.frm), "func": hex(f.start_ea) if f else None})
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("refs:", len(result["refs_to_5d5400"]))
    ida_pro.qexit(0)

main()
