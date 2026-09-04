'use strict';
/*
 * 网易易盾脱壳：内存扫描 dex 魔数 + dump
 * 用法: frida -H 127.0.0.1:27042 -f com.huachenjie.shandong_school -l dex_dump.js
 */
var OUT = '/data/local/tmp/sdxy_dump';
var dumped = {};

function scanAndDump() {
    var magics = [
        '64 65 78 0a 30 33 35 00', // dex\n035
        '64 65 78 0a 30 33 37 00', // dex\n037
        '64 65 78 0a 30 33 38 00', // dex\n038
        '64 65 78 0a 30 33 39 00', // dex\n039
        '64 65 79 0a 30 33 36 00', // dey\n036 (odex)
        '64 65 78 0a 30 34 31 00'  // dex\n041
    ];
    var found = 0;
    Process.enumerateRanges('r--').forEach(function (range) {
        magics.forEach(function (pat) {
            try {
                var ms = Memory.scanSync(range.base, range.size, pat);
                ms.forEach(function (m) {
                    var addr = m.address;
                    var key = addr.toString();
                    if (dumped[key]) return;
                    dumped[key] = true;
                    try {
                        var magic = addr.readByteArray(8);
                        var fileSize = addr.add(32).readU32();
                        if (fileSize < 0x1000 || fileSize > 0x40000000) {
                            return;
                        }
                        var data = addr.readByteArray(fileSize);
                        var fn = OUT + '/d_' + found + '_' + fileSize + '.dex';
                        var f = new File(fn, 'wb');
                        f.write(data);
                        f.close();
                        console.log('[+] ' + fn + ' @ ' + addr + ' size=' + fileSize);
                        found++;
                    } catch (e) {
                        console.log('[-] fail ' + addr + ' ' + e);
                    }
                });
            } catch (e) {}
        });
    });
    console.log('[+] total dumped: ' + found);
}

function enumerateClassLoaders() {
    try {
        Java.perform(function () {
            var loaders = Java.enumerateClassLoadersSync();
            console.log('[*] classloaders: ' + loaders.length);
            loaders.forEach(function (cl, i) {
                try {
                    var cls = cl.getClass().getName();
                    console.log('[*] loader[' + i + '] ' + cls);
                    // try dump via DexPathList dexElements
                    var c = cl.loadClass('dalvik.system.DexPathList');
                    if (c) {
                        var f = c.getDeclaredField('dexElements');
                        f.setAccessible(true);
                        var elems = f.get(cl);
                        var arr = Java.array('java.lang.Object', elems);
                        console.log('[*]   dexElements: ' + arr.length);
                        for (var j = 0; j < arr.length; j++) {
                            try {
                                var el = arr[j];
                                var ef = el.getClass().getDeclaredField('dexFile');
                                ef.setAccessible(true);
                                var df = ef.get(el);
                                var nf = df.getClass().getDeclaredField('mFileName');
                                nf.setAccessible(true);
                                var fn = nf.get(df);
                                console.log('[*]     dex[' + j + '] ' + fn);
                            } catch (e2) {}
                        }
                    }
                } catch (e) {}
            });
        });
    } catch (e) {
        console.log('[-] java enumerate fail ' + e);
    }
}

console.log('[*] dex_dump loaded, waiting 10s for shell to decrypt...');
setTimeout(function () {
    enumerateClassLoaders();
    scanAndDump();
    console.log('[*] done');
}, 10000);
