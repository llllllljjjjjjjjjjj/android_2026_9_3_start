'use strict';
/*
 * 验证 K.b2s（static native）与 DataComponent（实例 native）能否被 hook。
 * K 与 DataComponent 已在 base.apk（可加载），验证 Java.use + hook 安装成功。
 */
rpc.exports = {
    verify: function () {
        var out = {};
        Java.perform(function () {
            // 1. K.b2s（static native）
            try {
                var K = Java.use('com.huachenjie.c.K');
                out.K_loaded = true;
                out.K_methods = [];
                var methods = K.class.getDeclaredMethods();
                for (var i = 0; i < methods.length; i++) {
                    out.K_methods.push(methods[i].getName() + '(' + methods[i].getParameterTypes().length + ')');
                }
                // 尝试 hook（实现拦截，调用时打印，不改返回值）
                var origB2s = K.b2s;
                K.b2s.implementation = function (data, mode) {
                    var r = origB2s.call(this, data, mode);
                    send('K.b2s called mode=' + mode + ' ret=' + r);
                    return r;
                };
                out.K_b2s_hook = 'installed';
            } catch (e) {
                out.K_err = String(e);
            }

            // 2. DataComponent 方法存在性
            try {
                var DC = Java.use('com.huachenjie.running.service.DataComponent');
                out.DC_loaded = true;
                var dcMethods = DC.class.getDeclaredMethods();
                var names = {};
                for (var j = 0; j < dcMethods.length; j++) {
                    var m = dcMethods[j];
                    if (m.getModifiers() & 0x100) { // native
                        names[m.getName()] = true;
                    }
                }
                out.DC_native_methods = Object.keys(names).sort();
            } catch (e) {
                out.DC_err = String(e);
            }
        });
        return out;
    }
};
