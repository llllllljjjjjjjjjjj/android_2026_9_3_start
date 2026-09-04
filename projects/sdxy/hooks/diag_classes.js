'use strict';
rpc.exports = {
    diag: function () {
        var out = {};
        Java.perform(function () {
            var names = [
                'com.zj.widget.r01',
                'com.zj.widget.g33',
                'com.zj.widget.k14',
                'com.zj.widget.c23',
                'com.zj.widget.cq',
                'com.zj.widget.h58',
                'com.zj.widget.cl0',
                'huachenjie.sdk.http.security.core.EncryptInterceptor',
                'huachenjie.sdk.http.interceptor.ParamsInterceptor',
                'com.huachenjie.shandong_school.splash.SplashActivity',
                'com.huachenjie.shandong_school.ShandongApplication'
            ];
            var loaders = Java.enumerateClassLoadersSync();
            out.loaderCount = loaders.length;
            names.forEach(function (name) {
                var found = -1;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        var c = loaders[i].loadClass(name);
                        if (c != null) { found = i; break; }
                    } catch (e) {}
                }
                out[name] = found;
            });
        });
        return out;
    }
};
