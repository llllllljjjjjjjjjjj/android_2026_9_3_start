'use strict';
/*
 * spawn 早期 hook c23.e（密钥初始化）。轮询直到类可解析。
 * 避免 enumerateClassLoadersSync（触发检测），直接 Java.use 轮询。
 */
var hooked = false;
var attempts = 0;

function tryHook() {
    if (hooked) return;
    attempts++;
    Java.perform(function () {
        try {
            var c23 = Java.use('com.zj.widget.c23');
            c23.e.implementation = function (a, b, c, z1, z2, list) {
                send({
                    type: 'key',
                    a: String(a),
                    b: String(b),
                    c: String(c),
                    z1: z1,
                    z2: z2,
                    list: list != null ? list.toString() : null
                });
                return this.e(a, b, c, z1, z2, list);
            };
            hooked = true;
            console.log('[+] c23.e hooked after ' + attempts + ' attempts');
        } catch (e) {
            if (attempts % 20 === 0) {
                console.log('[-] c23 not ready (' + attempts + '): ' + e.message);
            }
        }
    });
    if (!hooked && attempts < 400) {
        setTimeout(tryHook, 250);
    }
}

setTimeout(tryHook, 1000);
