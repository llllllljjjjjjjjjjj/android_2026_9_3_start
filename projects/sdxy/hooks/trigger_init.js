'use strict';
/*
 * 主动调用 c80.e(context) 触发 k14.d -> c23.e 密钥初始化，再读 c23 静态字段。
 * c80 在已解密分片 s_41，其方法体完整；调用会触发 k14/c23 所在分片解密。
 */
rpc.exports = {
    trigger: function () {
        var out = {};
        Java.perform(function () {
            try {
                var loaders = Java.enumerateClassLoadersSync();
                var loader = null;
                var c80cls = null;
                var idx = -1;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        var c = loaders[i].loadClass('com.zj.widget.c80');
                        if (c != null) { c80cls = c; loader = loaders[i]; idx = i; break; }
                    } catch (e) {}
                }
                if (c80cls == null) { out.error = 'c80 not loadable'; return; }
                out.c80LoaderIdx = idx;

                // Context: ShandongApplication 静态实例 f7080a
                var appCtx = null;
                try {
                    var appCls = loader.loadClass('com.huachenjie.shandong_school.ShandongApplication');
                    var af = appCls.getDeclaredField('f7080a');
                    af.setAccessible(true);
                    appCtx = af.get(null);
                } catch (e) {
                    out.ctxErr = String(e);
                }
                if (appCtx == null) {
                    // fallback: MyApplication.getAppCtx()
                    try {
                        var myApp = loader.loadClass('com.netease.nis.wrapper.MyApplication');
                        var gm = myApp.getDeclaredMethod('getAppCtx');
                        gm.setAccessible(true);
                        appCtx = gm.invoke(null);
                    } catch (e2) {
                        out.ctxErr2 = String(e2);
                    }
                }
                if (appCtx == null) { out.error = 'no context'; return; }
                out.ctxClass = String(appCtx.getClass().getName());

                // c80.a singleton
                var af2 = c80cls.getDeclaredField('a');
                af2.setAccessible(true);
                var c80inst = af2.get(null);

                // invoke e(Context)
                var ContextClass = appCtx.getClass();
                var em = null;
                var ms = c80cls.getDeclaredMethods();
                for (var j = 0; j < ms.length; j++) {
                    if (ms[j].getName() === 'e' && ms[j].getParameterTypes().length === 1) {
                        em = ms[j];
                        break;
                    }
                }
                if (em == null) { out.error = 'e() not found'; return; }
                em.setAccessible(true);
                out.invokeStart = true;
                var ret = em.invoke(c80inst, appCtx);
                out.eRet = String(ret);

                // now read c23
                try {
                    var c23cls = loader.loadClass('com.zj.widget.c23');
                    var fa = c23cls.getDeclaredField('a'); fa.setAccessible(true);
                    var fb = c23cls.getDeclaredField('b'); fb.setAccessible(true);
                    out['c23.a'] = String(fa.get(null));
                    out['c23.b'] = String(fb.get(null));
                    out.c23Loaded = true;
                } catch (e3) {
                    out.c23Err = String(e3);
                }
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};
