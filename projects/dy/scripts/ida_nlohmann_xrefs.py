# IDA 9.2: 找 nlohmann/json 错误字符串的 xref，定位 native JSON 解析函数
import ida_auto, ida_pro, ida_funcs, idc, idautils, ida_idaapi
import json, time

OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\artifacts\nlohmann_xrefs.json"
# 关键错误字符串（nlohmann/json error_message）
KEYS = ["JSON must be UTF-8", "Dictionary keys must be quoted", "Number cannot be represented",
        "a JSON object must be UTF-8", "cannot create std::deque larger than max_size"]

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    result = {}
    for seg_name in (".rodata",):
        seg = idc.get_segm_by_sel(idc.selector_by_name(seg_name))
        if not seg:
            continue
        ea = idc.get_segm_start(seg)
        end = idc.get_segm_end(seg)
        cur = ea
        while cur < end:
            s = idc.get_strlit_contents(cur, -1, 0)
            if s:
                txt = s.decode(errors="ignore")
                for k in KEYS:
                    if k in txt:
                        xrefs = []
                        for xr in idautils.XrefsTo(cur, 0):
                            xrefs.append({"from": hex(xr.frm), "type": xr.type,
                                          "func": hex(ida_funcs.get_func(xr.frm).start_ea) if ida_funcs.get_func(xr.frm) else None})
                        result.setdefault(txt, []).append({"addr": hex(cur), "xrefs": xrefs})
                        break
                cur += len(s) + 1
            else:
                cur += 1
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    for k, v in result.items():
        print("STR", repr(k[:40]), "->")
        for x in v:
            for xr in x["xrefs"]:
                print("   xref from", xr["from"], "func", xr["func"])
    ida_pro.qexit(0)

main()
