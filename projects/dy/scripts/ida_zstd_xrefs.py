# IDA 9.2 headless: 找 libsscronet 里 ttnet zstd 组件字符串的 xref
import ida_auto, ida_pro, idc, ida_idaapi, idautils
import json, time

OUT = r"D:\reserve_agent\ish-portable-kit\projects\dy\artifacts\zstd_xrefs.json"
KEYS = ["ttnet_zstd_stream", "ttnet_zstd_dict_error", "TTNET_CONTENT_ZSTD_DECODING_FAILED",
        "request_ttzip_version", "response_ttzip_version", "zstd_prefix_path",
        "zstd_level", "zstd_dict", "ttnet_zstd"]

def main():
    t0 = time.time()
    while not ida_auto.auto_is_ok() and time.time() - t0 < 120:
        time.sleep(2)
    result = {}
    for seg_name in (".rodata", ".data.rel.ro", ".data", ".text"):
        seg = idc.get_segm_by_sel(idc.selector_by_name(seg_name))
        if not seg:
            continue
        ea = idc.get_segm_start(seg)
        end = idc.get_segm_end(seg)
        cur = ea
        cnt = 0
        while cur < end:
            s = idc.get_strlit_contents(cur, -1, 0)
            if s:
                txt = s.decode(errors="ignore")
                for k in KEYS:
                    if k in txt:
                        xrefs = []
                        for xr in idautils.XrefsTo(cur, 0):
                            xrefs.append({"from": hex(xr.frm), "type": xr.type})
                        result.setdefault(txt, []).append({"addr": hex(cur), "xrefs": xrefs})
                        break
                cur += len(s) + 1
            else:
                cur += 1
            cnt += 1
        print(seg_name, "done, scanned", cnt, "bytes-ish")
    with open(OUT, "w") as f:
        json.dump(result, f, indent=1)
    for k, v in result.items():
        print("STR", repr(k), ":", len(v), "refs")
        for x in v:
            for xr in x["xrefs"]:
                print("   xref from", xr["from"])
    ida_pro.qexit(0)

main()
