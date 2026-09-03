# IDA 9.2: 扫 sscronet 中签名头字符串的所有引用 (写回点定位)
import ida_auto, ida_pro, idc, ida_idaapi, ida_bytes, idautils
import json, time

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\sscronet_xrefs.json"
KEYS = ["x-argus", "x-gorgon", "x-ladon", "x-khronos", "x-helios", "x-medusa",
        "x-soter", "x-perseus", "x-tython", "x-ss-stub", "x-bogus"]

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 60:
        time.sleep(2)
    result = {}
    # 枚举 .rodata/.data 段中所有字符串
    for seg_name in (".rodata", ".data.rel.ro", ".data"):
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
                    if txt == k or (txt.startswith(k) and len(txt) < len(k) + 8):
                        xrefs = []
                        for xr in idautils.XrefsTo(cur, 0):
                            xrefs.append({"from": hex(xr.frm), "type": xr.type})
                        result.setdefault(k, []).append({"addr": hex(cur), "xrefs": xrefs})
                        break
                cur += len(s) + 1
            else:
                cur += 1
        print(seg_name, "done")
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    for k, v in result.items():
        print(k, ":", len(v), "strings,", sum(len(x["xrefs"]) for x in v), "xrefs")
    ida_pro.qexit(0)

main()
