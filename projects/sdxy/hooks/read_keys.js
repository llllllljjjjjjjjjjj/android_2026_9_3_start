'use strict';
/*
 * 纯读取：定位 ClassLoader 后读 c23 静态字段。不做任何 hook，降低检测面。
 */
rpc.exports = {
    dump: function () {
        var out = {};
        Java.perform(function () {
            try {
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
                out['c23.a'] = c23.a.value == null ? null : String(c23.a.value);
                out['c23.b'] = c23.b.value == null ? null : String(c23.b.value);
                out['c23.c'] = c23.c.value == null ? null : String(c23.c.value);
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
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};
