'use strict';
rpc.exports = {
    trigger: function () {
        var out = {};
        Java.perform(function () {
            try {
                var loaders = Java.enumerateClassLoadersSync();
                var loader = null;
                var encCls = null;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        var c = loaders[i].loadClass('huachenjie.sdk.http.security.core.EncryptInterceptor');
                        if (c != null) { encCls = c; loader = loaders[i]; break; }
                    } catch (e) {}
                }
                if (encCls == null) { out.error = 'no enc'; return; }
                Java.classFactory.loader = loader;

                // 触发 c23 解析
                var ctor = encCls.getDeclaredConstructor([]);
                ctor.setAccessible(true);
                var inst = ctor.newInstance([]);
                var dm = encCls.getDeclaredMethod('d', [loader.loadClass('java.lang.String')]);
                dm.setAccessible(true);
                dm.invoke(inst, ['{"data":{"phone":"13800138000"}}']);

                // 列出已加载类，找 c23/cq/r01
                var loaded = Java.enumerateLoadedClassesSync();
                out.loadedCount = loaded.length;
                var hits = loaded.filter(function (n) {
                    return n.indexOf('com.zj.widget') === 0 || n.indexOf('huachenjie.sdk') === 0;
                });
                out.zjWidgetLoaded = hits.slice(0, 100);

                // 尝试 Java.use
                try {
                    var c23 = Java.use('com.zj.widget.c23');
                    out['c23.a'] = c23.a.value == null ? null : String(c23.a.value);
                    out['c23.b'] = c23.b.value == null ? null : String(c23.b.value);
                    out['c23.c'] = c23.c.value == null ? null : String(c23.c.value);
                    out.useOk = true;
                } catch (e2) {
                    out.useErr = String(e2);
                }
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};
