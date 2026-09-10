#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""解析 dex 找 K 类（com.huachenjie.c.K）的类定义与方法签名，判断 b2s 是否 native。"""
import struct
import sys

TARGETS = ['Lcom/huachenjie/c/K;', 'com/huachenjie/c/K']


def uleb128(data, off):
    result = 0
    shift = 0
    while True:
        b = data[off]
        off += 1
        result |= (b & 0x7f) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, off


def read_string(data, off):
    # string_data_item: utf16_size(uleb128) + data + 0x00
    size, off = uleb128(data, off)
    # MUTF-8: 每个字符可能 1-3 字节
    end = data.index(b'\x00', off)
    s = data[off:end].decode('utf-8', errors='replace')
    return s, end + 1


def parse_dex(path):
    data = open(path, 'rb').read()
    if data[:4] != b'dex\n':
        return None
    header = struct.unpack_from('<I', data, 32)[0]  # file_size
    # dex 035 header 偏移
    string_ids_size = struct.unpack_from('<I', data, 0x38)[0]
    string_ids_off = struct.unpack_from('<I', data, 0x3c)[0]
    type_ids_size = struct.unpack_from('<I', data, 0x40)[0]
    type_ids_off = struct.unpack_from('<I', data, 0x44)[0]
    class_defs_size = struct.unpack_from('<I', data, 0x60)[0]
    class_defs_off = struct.unpack_from('<I', data, 0x64)[0]
    method_ids_size = struct.unpack_from('<I', data, 0x58)[0]
    method_ids_off = struct.unpack_from('<I', data, 0x5c)[0]
    proto_ids_size = struct.unpack_from('<I', data, 0x48)[0]
    proto_ids_off = struct.unpack_from('<I', data, 0x4c)[0]
    return (data, class_defs_size, class_defs_off, type_ids_size, type_ids_off,
            string_ids_size, string_ids_off, method_ids_size, method_ids_off,
            proto_ids_size, proto_ids_off)


def method_name(data, idx, method_ids_off, string_ids_off, type_ids_off, proto_ids_off):
    # method_id_item: class_idx(2) proto_idx(2) name_idx(4)
    m_off = method_ids_off + idx * 8
    class_idx = struct.unpack_from('<H', data, m_off)[0]
    proto_idx = struct.unpack_from('<H', data, m_off + 2)[0]
    name_idx = struct.unpack_from('<I', data, m_off + 4)[0]
    # name
    sid_off = string_ids_off + name_idx * 4
    sdata_off = struct.unpack_from('<I', data, sid_off)[0]
    name, _ = read_string(data, sdata_off)
    # class descriptor
    tid_off = type_ids_off + class_idx * 4
    desc_idx = struct.unpack_from('<I', data, tid_off)[0]
    sid_off2 = string_ids_off + desc_idx * 4
    sdata_off2 = struct.unpack_from('<I', data, sid_off2)[0]
    cls, _ = read_string(data, sdata_off2)
    # proto: shorty_idx(4) return_type_idx(4) params_off(4)
    p_off = proto_ids_off + proto_idx * 12
    ret_type_idx = struct.unpack_from('<I', data, p_off + 4)[0]
    tid_off3 = type_ids_off + ret_type_idx * 4
    desc_idx3 = struct.unpack_from('<I', data, tid_off3)[0]
    sid_off3 = string_ids_off + desc_idx3 * 4
    sdata_off3 = struct.unpack_from('<I', data, sid_off3)[0]
    ret, _ = read_string(data, sdata_off3)
    return name, cls, ret


def main():
    for dex in ['projects/sdxy/apk/dump/sdxy_dump/s_45_6997568.dex',
                'projects/sdxy/apk/dump/sdxy_dump/s_54_9205764.dex']:
        r = parse_dex(dex)
        if not r:
            print(f'[-] {dex}: not dex')
            continue
        (data, cds, cdo, tns, tno, sns, sno,
         mns, mno, pns, pno) = r
        print(f'\n=== {dex} ===')
        print(f'class_defs_size={cds} off=0x{cdo:x} method_ids={mns}')
        # 遍历 class_def，找 K 类
        for i in range(cds):
            cd_off = cdo + i * 32
            class_idx = struct.unpack_from('<I', data, cd_off)[0]
            access_flags = struct.unpack_from('<I', data, cd_off + 4)[0]
            # type_id -> descriptor_idx -> string
            tid_off = tno + class_idx * 4
            desc_idx = struct.unpack_from('<I', data, tid_off)[0]
            # string_id -> string_data_off
            sid_off = sno + desc_idx * 4
            sdata_off = struct.unpack_from('<I', data, sid_off)[0]
            desc, _ = read_string(data, sdata_off)
            if 'huachenjie/c/K' in desc or desc in TARGETS:
                print(f'  FOUND class: {desc} access=0x{access_flags:x}')
                # class_data_off
                cd_off2 = struct.unpack_from('<I', data, cd_off + 24)[0]
                print(f'    class_data_off=0x{cd_off2:x}')
                if cd_off2:
                    off = cd_off2
                    static_fields, off = uleb128(data, off)
                    instance_fields, off = uleb128(data, off)
                    direct_methods, off = uleb128(data, off)
                    virtual_methods, off = uleb128(data, off)
                    print(f'    static_fields={static_fields} instance_fields={instance_fields} '
                          f'direct_methods={direct_methods} virtual_methods={virtual_methods}')
                    last_idx = 0
                    for m in range(direct_methods + virtual_methods):
                        diff, off = uleb128(data, off)
                        last_idx += diff
                        mflags, off = uleb128(data, off)
                        code_off, off = uleb128(data, off)
                        is_native = bool(mflags & 0x0100)
                        is_static = bool(mflags & 0x0008)
                        name, cls, ret = method_name(data, last_idx, mno, sno, tno, pno)
                        print(f'      method idx={last_idx} name={name} ret={ret} '
                              f'flags=0x{mflags:x} native={is_native} static={is_static} code_off=0x{code_off:x}')


if __name__ == '__main__':
    main()
