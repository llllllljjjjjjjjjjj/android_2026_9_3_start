# 找 sscronet 中所有引用 metasec 相关字符串的位置
import ida_auto, ida_pro, idautils, idc, ida_idaapi
import json

OUT = r"D:\reserve_agent\skills-portable-test\projects\dy\artifacts\metasec_refs.json"
KEYS = ["metasec", "ms.bd", "getGorgon", "getArgus", "getLadon", "getKhronos",
        "getHelios", "getMedusa", "getSoter", "getPerseus", "getTython", "JNI"]

def main():
    ida_auto.auto_wait()
    results = {}
    for s, ea in idautils.Strings():
        st = str(s)
        for k in KEYS:
            if k.lower() in st.lower():
                xrefs = []
                for xr in idautils.XrefsTo(ea):
                    xrefs.append({"from": hex(xr.frm), "type": xr.type})
                results[hex(ea)] = {"str": st, "xrefs": xrefs}
                break
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    print("found", len(results), "strings")
    ida_pro.qexit(0)

main()
