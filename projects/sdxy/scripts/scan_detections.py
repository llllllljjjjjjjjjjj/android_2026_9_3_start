#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全项目扫描检测点（单次读取，预编译正则，高效）。"""
import glob
import os
import re

ROOT = r'projects\sdxy\decompiled_biz\all\sources'

GROUPS = {
    "ROOT检测": [r'isRooted', r'RootBeer', r'checkRoot', r'Magisk', r'magisk',
                 r'/system/bin/su', r'which su', r'Superuser', r'com\.topjohnwu'],
    "FRIDA检测": [r'frida', r'gum-js-loop', r'gmain', r'linjector', r'frida-agent'],
    "XPOSED检测": [r'xposed', r'lsposed', r'edxposed', r'XposedBridge', r'de\.robv\.android\.xposed'],
    "模拟器检测": [r'isEmulator', r'emulator', r'qemu', r'goldfish', r'ranchu', r'vbox',
                   r'vmos', r'模拟器', r'MuMu', r'BlueStacks'],
    "多开/分身检测": [r'virtualapp', r'多开', r'分身', r'parallel', r'VirtualXposed',
                      r'com\.lbe\.parallel', r'isVirtual'],
    "反调试": [r'TracerPid', r'ptrace', r'isDebuggerConnected', r'anti.?debug',
               r'Debug\.isDebugger', r'waitForDebugger'],
    "反注入/反Hook": [r'/proc/self/maps', r'proc/self/status', r'frida', r'gum',
                      r'Interceptor', r'art hook', r'ART hook'],
    "代理/VPN检测": [r'proxy', r'vpn', r'代理', r'抓包', r'capture', r'tcpdump',
                     r'http_proxy', r'VpnService', r'TRANSPORT_VPN'],
    "设备指纹采集": [r'getDeviceId', r'getSubscriberId', r'getImei', r'imei',
                     r'androidId', r'ANDROID_ID', r'oaid', r'OAID', r'getMacAddress',
                     r'Build\.SERIAL', r'getSerial', r'Build\.FINGERPRINT'],
    "风控关键词": [r'风控', r'riskControl', r'risk_control', r'blacklist', r'黑名单',
                   r'deviceRisk', r'riskLevel', r'securityCheck', r'设备风险'],
    "签名校验": [r'checkSignature', r'GET_SIGNATURES', r'签名校验', r'nativesign',
                 r'reflectsign', r'getPackageInfo.*signature'],
    "应用/进程枚举": [r'getInstalledPackages', r'getRunningProcesses', r'getRunningTasks',
                      r'getInstalledApplications', r'getSensorList'],
}

# 预编译（大小写不敏感）
COMPILED = {g: [re.compile(p, re.IGNORECASE) for p in pats] for g, pats in GROUPS.items()}


def scan():
    files = glob.glob(os.path.join(ROOT, '**', '*.java'), recursive=True)
    print(f'[+] scanning {len(files)} java files')
    result = {g: {} for g in GROUPS}

    for f in files:
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                text = fh.read()
        except Exception:
            continue
        lines = text.split('\n')
        rel = f.replace(ROOT + os.sep, '').replace(os.sep, '/')
        for group, pats in COMPILED.items():
            matched = []
            for p in pats:
                m = p.search(text)
                if m:
                    ln = text[:m.start()].count('\n') + 1
                    line = lines[ln - 1].strip()[:130]
                    matched.append(f'L{ln}: {line}')
            if matched:
                result[group][rel] = matched[:4]

    for group in GROUPS:
        hits = result[group]
        print(f'\n[{"="*6} {group} | 命中 {len(hits)} 文件 {"="*6}]')
        for rel, ms in list(hits.items())[:25]:
            print(f'  {rel}')
            for m in ms:
                print(f'    {m}')
        if len(hits) > 25:
            print(f'  ... 另有 {len(hits)-25} 个文件')


if __name__ == '__main__':
    scan()
