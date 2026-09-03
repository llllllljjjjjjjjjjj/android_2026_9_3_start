# IDA 9.2: 找 0x49a720 的调用者 + 0x49bb9c 字典错误函数的完整反汇编
import ida_auto, ida_pro, ida_funcs, idc, idautils, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\artifacts\zstd_callers.json"

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    result = {}
    # 0x49a720 调用者
    callers = []
    for xr in idautils.XrefsTo(0x49a720, 0):
        callers.append({"from": hex(xr.frm), "type": xr.type})
    result["0x49a720_callers"] = callers
    print("0x49a720 callers:", callers)
    # 0x49bb9c 调用者
    callers2 = []
    for xr in idautils.XrefsTo(0x49bb9c, 0):
        callers2.append({"from": hex(xr.frm), "type": xr.type})
    result["0x49bb9c_callers"] = callers2
    print("0x49bb9c callers:", callers2)
    # 0x49e054 / 0x49a060 调用者（zstd stream 上报）
    for f in (0x49e054, 0x49a060, 0x49dfa0):
        cl = []
        for xr in idautils.XrefsTo(f, 0):
            cl.append({"from": hex(xr.frm), "type": xr.type})
        result[hex(f) + "_callers"] = cl
        print(hex(f), "callers:", cl)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("saved", OUT)
    ida_pro.qexit(0)

main()
