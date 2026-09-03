# IDA 9.2: dump 0x5d5488 附近 API 表结构 (魔改 Cronet 导出表)
import ida_auto, ida_pro, idc, ida_idaapi, ida_bytes
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\ida_api_table.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {"qwords": [], "refs_to_5d5488": []}
    # dump qwords 0x5d5400-0x5d5600
    ea = 0x5d5400
    while ea < 0x5d5600:
        v = idc.get_qword(ea)
        nm = idc.get_name(v) or ""
        result["qwords"].append({"ea": hex(ea), "val": hex(v), "name": nm})
        ea += 8
    # 谁引用 0x5d5488
    import idautils
    for xr in idautils.XrefsTo(0x5d5488, 0):
        result["refs_to_5d5488"].append({"from": hex(xr.frm), "type": xr.type})
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("done, refs:", len(result["refs_to_5d5488"]))
    ida_pro.qexit(0)

main()
