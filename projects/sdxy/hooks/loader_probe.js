'use strict';
/*
 * 枚举所有 ClassLoader 的 dex 文件路径 + dump 主 loader 的 dex
 */
var Array = Java.use('java.lang.reflect.Array');

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

function probe() {
    Java.perform(function () {
        var loaders = Java.enumerateClassLoadersSync();
        console.log('[*] total loaders: ' + loaders.length);
        loaders.forEach(function (cl, i) {
            try {
                var cls = cl.getClass().getName();
                var plField = getField(cl.getClass(), 'pathList');
                if (plField == null) {
                    console.log('[' + i + '] ' + cls + ' (no pathList)');
                    return;
                }
                var pathList = plField.get(cl);
                var deField = getField(pathList.getClass(), 'dexElements');
                if (deField == null) {
                    console.log('[' + i + '] ' + cls + ' (no dexElements)');
                    return;
                }
                var elements = deField.get(pathList);
                var len = Array.getLength(elements);
                console.log('[' + i + '] ' + cls + ' dexElements=' + len);
                for (var j = 0; j < len; j++) {
                    try {
                        var el = Array.get(elements, j);
                        if (el == null) continue;
                        var dfField = getField(el.getClass(), 'dexFile');
                        if (dfField == null) continue;
                        var df = dfField.get(el);
                        if (df == null) continue;
                        var nf = getField(df.getClass(), 'mFileName');
                        var fn = nf != null ? String(nf.get(df)) : '(no mFileName)';
                        var cf = getField(df.getClass(), 'mCookie');
                        var cookie = cf != null ? cf.get(df) : null;
                        console.log('    dex[' + j + '] file=' + fn + ' cookie=' + cookie);
                    } catch (e2) {
                        console.log('    dex[' + j + '] err ' + e2);
                    }
                }
            } catch (e) {
                console.log('[' + i + '] err ' + e);
            }
        });
    });
}

console.log('[*] loader_probe loaded, wait 8s...');
setTimeout(probe, 8000);
