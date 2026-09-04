'use strict';
/*
 * 用 loadClass（ART FindClass 走 cookie 重定向）+ 反射读静态字段，
 * 绕开 Java.use 无法解析 stub.dex 的限制。
 */
rpc.exports = {
    dump: function () {
        var out = {};
        Java.perform(function () {
            try {
                var loaders = Java.enumerateClassLoadersSync();
                var cls = null;
                var idx = -1;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        var c = loaders[i].loadClass('com.zj.widget.c23');
                        if (c != null) { cls = c; idx = i; break; }
                    } catch (e) {}
                }
                if (cls == null) {
                    out.error = 'class not loadable';
                    return;
                }
                out.loaderIdx = idx;
                out.loaderClass = String(loaders[idx].getClass().getName());
                function readStatic(name) {
                    try {
                        var f = cls.getDeclaredField(name);
                        f.setAccessible(true);
                        var v = f.get(null);
                        return v == null ? null : String(v);
                    } catch (e) {
                        return 'ERR:' + e.message;
                    }
                }
                out['c23.a'] = readStatic('a');
                out['c23.b'] = readStatic('b');
                out['c23.c'] = readStatic('c');
                out['c23.f11071a'] = readStatic('f11071a');
                out['c23.f11072b'] = readStatic('f11072b');
                out['c23.f11073c'] = readStatic('f11073c');
                // field list
                try {
                    var fl = cls.getDeclaredField('f11070a');
                    fl.setAccessible(true);
                    var list = fl.get(null);
                    if (list != null) {
                        var arr = [];
                        var it = Java.use('java.util.List').$new ? null : null;
                        var size = list.size();
                        for (var j = 0; j < size && j < 80; j++) {
                            arr.push(String(list.get(j)));
                        }
                        out['c23.f11070a.size'] = size;
                        out['c23.f11070a'] = arr;
                    }
                } catch (e2) {
                    out.f11070a_err = String(e2);
                }
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};
