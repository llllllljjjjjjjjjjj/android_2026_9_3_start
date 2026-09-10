'use strict';
/* 遍历所有 classLoader，检查加密类是否已加载（决定 loadClass 兜底是否够）。 */
rpc.exports = {
    check: function () {
        var out = {};
        Java.perform(function () {
            var loaders = Java.enumerateClassLoadersSync();
            var targets = [
                'com.zj.widget.c23', 'com.zj.widget.mp8', 'com.zj.widget.qf7',
                'com.zj.widget.a15', 'com.zj.widget.cq', 'com.zj.widget.k14',
                'huachenjie.sdk.http.interceptor.ParamsInterceptor'
            ];
            out.loaderCount = loaders.length;
            out.found = {};
            for (var i = 0; i < loaders.length; i++) {
                var loaderClass = loaders[i].getClass().getName();
                for (var j = 0; j < targets.length; j++) {
                    try {
                        var c = loaders[i].loadClass(targets[j]);
                        if (c != null && !out.found[targets[j]]) {
                            out.found[targets[j]] = 'loader[' + i + ']=' + loaderClass;
                        }
                    } catch (e) {
                    }
                }
            }
        });
        return out;
    }
};
