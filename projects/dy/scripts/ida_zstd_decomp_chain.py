# IDA 9.2: 找统计序列化函数 0x499f00 的调用者 + 追解压链
import ida_auto, ida_pro, ida_funcs, idc, idautils, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\artifacts\zstd_decomp_chain.json"

def func_of(ea):
    fn = ida_funcs.get_func(ea)
    return hex(fn.start_ea) if fn else None

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    result = {}
    # 0x499f00 调用者
    callers = []
    for xr in idautils.XrefsTo(0x499f00, 0):
        callers.append({"from": hex(xr.frm), "type": xr.type, "func": func_of(xr.frm)})
    result["0x499f00_callers"] = callers
    print("0x499f00 callers:", callers)
    # 同样找 0x49e054 所在函数 + 0x49dfa0 所在函数的调用者
    for f in (0x49e054, 0x49dfa0, 0x49bb9c):
        fn = ida_funcs.get_func(f)
        if fn:
            cl = []
            for xr in idautils.XrefsTo(fn.start_ea, 0):
                cl.append({"from": hex(xr.frm), "type": xr.type, "func": func_of(xr.frm)})
            result[hex(fn.start_ea) + "_callers"] = cl
            print(hex(fn.start_ea), "callers:", cl)
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    print("saved", OUT)
    ida_pro.qexit(0)

main()
