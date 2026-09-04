'use strict';
/*
 * Attach 到运行中进程：枚举 ClassLoader，定位能加载业务类的 loader 及其 dex 来源。
 * 不 dump，仅侦察。
 */
var TARGET_CLASS = 'com.huachenjie.shandong_school.splash.SplashActivity';

function getField(clazz, name) {
    var c = clazz;
    while (c != null) {
        try {
            var f = c.getDeclaredField(name);
            f.setAccessible(true);
            return f;
        } catch (e) {
            c = c.getSuperclass();
        }
    }
    return null;
}

function dexFileName(df) {
    try {
        var nf = getField(df.getClass(), 'mFileName');
        if (nf != null) return String(nf.get(df));
    } catch (e) {}
    return '(unknown)';
}

function probe() {
    Java.perform(function () {
        var loaders = Java.enumerateClassLoadersSync();
        console.log('[+] total classloaders = ' + loaders.length);
        loaders.forEach(function (cl, i) {
            var info = '';
            try {
                var cls = cl.getClass().getName();
                info = cls;
                var plField = getField(cl.getClass(), 'pathList');
                if (plField != null) {
                    var pathList = plField.get(cl);
                    var deField = getField(pathList.getClass(), 'dexElements');
                    if (deField != null) {
                        var elements = deField.get(pathList);
                        var len = Java.use('java.lang.reflect.Array').getLength(elements);
                        info += ' dexElements=' + len;
                        var names = [];
                        for (var j = 0; j < len && j < 6; j++) {
                            try {
                                var el = Java.use('java.lang.reflect.Array').get(elements, j);
                                if (el == null) continue;
                                var dfField = getField(el.getClass(), 'dexFile');
                                if (dfField == null) continue;
                                var df = dfField.get(el);
                                if (df == null) continue;
                                names.push(dexFileName(df));
                            } catch (e2) {}
                        }
                        if (names.length) info += ' dexs=' + names.join(' | ');
                    }
                }
                // try load business class
                try {
                    var c = cl.loadClass(TARGET_CLASS);
                    info += ' [HIT: ' + TARGET_CLASS + ' -> ' + c + ']';
                } catch (e3) {
                    // not this loader
                }
                console.log('[' + i + '] ' + info);
            } catch (e) {
                console.log('[' + i + '] err ' + e);
            }
        });
        console.log('[+] probe done');
    });
}

setImmediate(probe);
