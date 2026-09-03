# 合并运行时 dump → libmetasec_ml_dec.so（含 rwxp 页 + BSS 运行时数据）
# 布局（对应 maps）：
#   file 0x0        -0x280000 : metasec1.bin  (r-xp seg1, vaddr 0)
#   file 0x280000   -0x281000 : m_rwxp.bin    (rwxp 页, vaddr 0x280000)
#   file 0x281000   -0x34D000 : metasec2.bin  (r-xp seg2, vaddr 0x281000)
#   file 0x375000   -0x3CE000 : metasec3.bin  (rw-p 数据, vaddr 0x37D000)
#   file 0x3CE000   -0x3E1000 : m_bss.bin     (anon:.bss, vaddr 0x3D7000; off = 0x375650+(0x3D7000-0x37D650) = 0x3CE000)
#   seg3 phdr filesz 0x58218 -> 0x6A9B0 (覆盖到 vaddr 0x3E8000, 映射 bss)
import struct, os

D = r"D:\reserve_agent\skills-portable-test\projects\dy\so_analysis"
orig = open(os.path.join(D, "libmetasec_ml.so"), "rb").read()
print("orig size = %#x" % len(orig))

seg1 = open(os.path.join(D, "metasec1.bin"), "rb").read()
rwxp = open(os.path.join(D, "m_rwxp.bin"), "rb").read()
seg2 = open(os.path.join(D, "metasec2.bin"), "rb").read()
seg3 = open(os.path.join(D, "metasec3.bin"), "rb").read()
bss = open(os.path.join(D, "m_bss.bin"), "rb").read()
print("seg1=%#x rwxp=%#x seg2=%#x seg3=%#x bss=%#x" % (len(seg1), len(rwxp), len(seg2), len(seg3), len(bss)))

# 验证 rwxp 页与 hook19 运行时字节一致（0x28065c 处）
assert rwxp[0x65C:0x668].hex().startswith("ff0303d1fd7b06a9fd830191"), "rwxp page mismatch: %s" % rwxp[0x65C:0x668].hex()
print("rwxp[0x65c] =", rwxp[0x65C:0x680].hex())

# 验证 seg2 头部有效代码（0x281000 处，应是指令非全 0xff）
print("seg2[0:16] =", seg2[:16].hex())

# 检查 bss 中全局区 0x3E5F94 的内容（bss 偏移 = 0x3E5F94-0x3D7000 = 0xFF94）
print("bss len=%#x" % len(bss))
print("bss[0xFF94:0xFFC0] =", bss[0xFF94:0xFFC0].hex())

NEWSZ = 0x3E2000
out = bytearray(orig)
if len(out) < NEWSZ:
    out += b"\x00" * (NEWSZ - len(out))

# 覆盖解密/运行时数据
out[0x000000:0x280000] = seg1
out[0x280000:0x281000] = rwxp
out[0x281000:0x34D000] = seg2
out[0x375000:0x3CE000] = seg3
out[0x3CE000:0x3CE000 + len(bss)] = bss

# 修改 seg3 phdr filesz: 0x58218 -> 0x6A9B0 (vaddr 0x37D650..0x3E8000)
e_phoff = struct.unpack_from("<Q", out, 32)[0]
e_phentsize = struct.unpack_from("<H", out, 54)[0]
e_phnum = struct.unpack_from("<H", out, 56)[0]
patched = False
for i in range(e_phnum):
    o = e_phoff + i * e_phentsize
    p_type = struct.unpack_from("<I", out, o)[0]
    if p_type == 1:  # PT_LOAD
        p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from("<QQQQQQ", out, o + 8)
        if p_vaddr == 0x37D650:
            assert p_filesz == 0x58218, "unexpected filesz %#x" % p_filesz
            struct.pack_into("<Q", out, o + 8 + 24, 0x6AAE0)  # p_filesz -> 覆盖到 vaddr 0x3E8130
            print("patched seg3 filesz 0x58218 -> 0x6AAE0")
            patched = True
assert patched, "seg3 not found"

final = bytes(out[:NEWSZ])
path = os.path.join(D, "libmetasec_ml_dec.so")
open(path, "wb").write(final)
print("wrote", path, "%#x" % len(final))
# 最终校验
print("dec[0x28065c:0x280668] =", final[0x28065C:0x280668].hex())
