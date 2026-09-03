/*
 * 大众点评 mtgsig 在线 oracle 采集 Hook
 * 目标: com.dianping.v1
 * 采集链: ApiModelTools.m6460d (签名入口, 完整请求)
 *         -> MTGuard.requestSignatureForBabelV4 (mtgsig 输入/输出)
 *         -> MTGuard.userIdentification (siua 设备指纹)
 *
 * 用法:
 *   frida -U -f com.dianping.v1 -l mtgsig_oracle.js --no-pause
 * 或 attach:
 *   frida -U -n 大众点评 -l mtgsig_oracle.js
 */

function bytesToStr(arr) {
    try {
        var s = '';
        for (var i = 0; i < arr.length; i++) {
            s += String.fromCharCode(arr[i] & 0xff);
        }
        return s;
    } catch (e) {
        return '';
    }
}

function bytesToHex(arr) {
    var h = '';
    for (var i = 0; i < arr.length; i++) {
        h += ('0' + (arr[i] & 0xff).toString(16)).slice(-2);
    }
    return h;
}

Java.perform(function () {
    var hooked = {};

    // ---- 1. 签名入口: ApiModelTools.m6460d(Request) ----
    try {
        var ApiModelTools = Java.use("com.dianping.apimodel.ApiModelTools");
        var Request = Java.use("com.dianping.nvnetwork.Request");
        ApiModelTools.m6460d.overload('com.dianping.nvnetwork.Request').implementation = function (req) {
            var url = '', method = '', headersBefore = {};
            try {
                url = req.url();
                method = req.method();
                var hs = req.headers();
                if (hs) {
                    var it = hs.entrySet().iterator();
                    while (it.hasNext()) {
                        var e = it.next();
                        headersBefore[e.getKey()] = e.getValue();
                    }
                }
            } catch (e) {}
            var out = this.m6460d(req);
            var headersAfter = {};
            try {
                var hs2 = out.headers();
                if (hs2) {
                    var it2 = hs2.entrySet().iterator();
                    while (it2.hasNext()) {
                        var e2 = it2.next();
                        headersAfter[e2.getKey()] = e2.getValue();
                    }
                }
            } catch (e) {}
            send({
                type: 'm6460d',
                method: method,
                url: url,
                mtgsig: headersAfter['mtgsig'] || headersAfter['mtgsig'.toLowerCase()] || null,
                siua: headersAfter['siua'] || headersAfter['siua'.toLowerCase()] || null,
                headers: headersAfter
            });
            return out;
        };
        console.log('[+] hooked ApiModelTools.m6460d');
    } catch (e) {
        console.log('[-] m6460d hook fail: ' + e);
    }

    // ---- 2. mtgsig 核心: MTGuard.requestSignatureForBabelV4 ----
    try {
        var MTGuard = Java.use("com.meituan.android.common.mtguard.MTGuard");
        MTGuard.requestSignatureForBabelV4.overload(
            'java.lang.String', 'java.lang.String', 'java.lang.String',
            'java.lang.String', 'java.lang.String', '[B'
        ).implementation = function (method, url, ua, ce, ct, body) {
            var ret = this.requestSignatureForBabelV4(method, url, ua, ce, ct, body);
            var sig = null;
            try {
                if (ret && ret.get) {
                    var v = ret.get('mtgsig');
                    sig = (v === null || v === undefined) ? null : String(v);
                }
            } catch (e) {}
            send({
                type: 'babelV4',
                method: method,
                url: url,
                ua: ua,
                contentEncoding: ce,
                contentType: ct,
                bodyHex: body ? bytesToHex(Java.array('byte', body)) : '',
                bodyStr: body ? bytesToStr(Java.array('byte', body)) : '',
                bodyLen: body ? body.length : 0,
                mtgsig: sig
            });
            return ret;
        };
        console.log('[+] hooked MTGuard.requestSignatureForBabelV4');
    } catch (e) {
        console.log('[-] babelV4 hook fail: ' + e);
    }

    // ---- 3. siua 设备指纹 ----
    try {
        var MTGuard2 = Java.use("com.meituan.android.common.mtguard.MTGuard");
        MTGuard2.userIdentification.implementation = function () {
            var b = this.userIdentification();
            send({ type: 'siua', siua: b ? bytesToStr(Java.array('byte', b)) : null, siuaHex: b ? bytesToHex(Java.array('byte', b)) : null });
            return b;
        };
        console.log('[+] hooked MTGuard.userIdentification');
    } catch (e) {
        console.log('[-] userIdentification hook fail: ' + e);
    }

    // ---- 4. native 精确输入: MainBridge.main3 / ShellBridge.main3 (类加载器兼容) ----
    function hookBridgeMain3(className) {
        try {
            var B = Java.use(className);
            B.main3.implementation = function (i, objArr) {
                var ret = this.main3(i, objArr);
                if (i === 2) {
                    try {
                        var input = '', host = '', sig = null;
                        if (objArr && objArr.length >= 2) {
                            var b0 = Java.array('byte', objArr[0]);
                            var b1 = Java.array('byte', objArr[1]);
                            input = bytesToStr(b0);
                            host = bytesToStr(b1);
                        }
                        if (ret && ret.length > 0) {
                            var v = ret[0];
                            sig = (v === null || v === undefined) ? null : String(v);
                        }
                        send({ type: 'native_main2', cls: className, input: input, inputHex: bytesToHex(Java.array('byte', objArr[0])), host: host, sig: sig });
                    } catch (e) {
                        send({ type: 'native_main2_err', err: String(e) });
                    }
                }
                return ret;
            };
            console.log('[+] hooked main3 of ' + className);
        } catch (e) {
            console.log('[-] main3 hook fail for ' + className + ': ' + e);
        }
    }
    try {
        hookBridgeMain3('com.meituan.android.common.mtguard.MainBridge');
    } catch (e) {}
    try {
        hookBridgeMain3('com.meituan.android.common.mtguard.ShellBridge');
    } catch (e) {}
    Java.enumerateLoadedClasses({
        onMatch: function (className) {
            if (className.indexOf('mtguard') !== -1 && (className.indexOf('Bridge') !== -1)) {
                hookBridgeMain3(className);
            }
        },
        onComplete: function () {}
    });
});
