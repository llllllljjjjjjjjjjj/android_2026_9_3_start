'use strict';
/*
 * 定位能加载 com.zj.widget.c23 的 ClassLoader，读取密钥 + hook 加解密。
 */
rpc.exports = {
    dump: function () {
        var out = {};
        Java.perform(function () {
            try {
                // find correct classloader
                var loaders = Java.enumerateClassLoadersSync();
                var target = null;
                var idx = -1;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        loaders[i].loadClass('com.zj.widget.c23');
                        target = loaders[i];
                        idx = i;
                        break;
                    } catch (e) {}
                }
                if (target == null) {
                    out.error = 'no loader for com.zj.widget.c23';
                    return;
                }
                out.loaderIdx = idx;
                out.loaderClass = target.getClass().getName();
                Java.classFactory.loader = target;

                var c23 = Java.use('com.zj.widget.c23');
                out['c23.a'] = String(c23.a.value);
                out['c23.b'] = String(c23.b.value);
                out['c23.c'] = String(c23.c.value);
                var list = c23.f11070a.value;
                if (list) {
                    var arr = [];
                    var it = list.iterator();
                    var n = 0;
                    while (it.hasNext() && n < 80) { arr.push(String(it.next())); n++; }
                    out['c23.f11070a'] = arr;
                    out['c23.f11070a.size'] = list.size();
                } else {
                    out['c23.f11070a'] = null;
                }
                out['c23.f11071a'] = c23.f11071a.value;
                out['c23.f11072b'] = c23.f11072b.value;
                out['c23.f11073c'] = c23.f11073c.value;

                // also dump mo1 (Authorization/satoken holder) if resolvable
                try {
                    var mo1 = Java.use('com.zj.widget.mo1');
                    out['mo1.f12470a'] = mo1.f12470a.value != null ? String(mo1.f12470a.value) : null;
                    out['mo1.b'] = mo1.b.value != null ? String(mo1.b.value) : null;
                } catch (e2) {
                    out.mo1_err = String(e2);
                }
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};

Java.perform(function () {
    // hook after loader known; hooking is best-effort
    try {
        var loaders = Java.enumerateClassLoadersSync();
        for (var i = 0; i < loaders.length; i++) {
            try {
                loaders[i].loadClass('com.zj.widget.cq');
                Java.classFactory.loader = loaders[i];
                break;
            } catch (e) {}
        }
        var cq = Java.use('com.zj.widget.cq');
        cq.c.overload('java.lang.String', 'java.lang.String').implementation = function (plain, key) {
            var r = this.c(plain, key);
            console.log('[cq.c ENC] plain=' + plain + ' key=' + key + ' -> ' + r);
            return r;
        };
        console.log('[*] cq.c hooked');
    } catch (e) {
        console.log('[-] hook cq.c fail: ' + e);
    }
});
