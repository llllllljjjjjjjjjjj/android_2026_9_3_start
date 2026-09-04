'use strict';
/*
 * Attach 到已运行进程，扫描内存中的 dex magic 并 dump 到 /data/local/tmp/sdxy_dump/。
 * 业务类已加载，ART 必然把类定义明文驻留内存，可扫到。
 */
var OUT = '/data/data/com.huachenjie.shandong_school/files/dump';
var dumped = {};

function dumpRange() {
    var patterns = [
        '64 65 78 0a 30 33 35 00',
        '64 65 78 0a 30 33 37 00',
        '64 65 78 0a 30 33 38 00',
        '64 65 78 0a 30 33 39 00'
    ];
    var found = 0;
    var ranges = Process.enumerateRanges({ protection: 'r--', coalesce: true })
        .concat(Process.enumerateRanges({ protection: 'rw-', coalesce: true }));
    console.log('[+] ranges to scan: ' + ranges.length);
    ranges.forEach(function (range) {
        if (range.size > 0x40000000) return; // skip huge
        patterns.forEach(function (pat) {
            try {
                var ms = Memory.scanSync(range.base, range.size, pat);
                ms.forEach(function (m) {
                    var addr = m.address;
                    var key = addr.toString();
                    if (dumped[key]) return;
                    dumped[key] = true;
                    try {
                        var fileSize = addr.add(32).readU32();
                        if (fileSize < 0x200 || fileSize > 0x30000000) return;
                        // header_size sanity
                        var headerSize = addr.add(36).readU32();
                        if (headerSize !== 0x70) return;
                        var data = addr.readByteArray(fileSize);
                        var fn = OUT + '/s_' + found + '_' + fileSize + '.dex';
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

Java.perform(function () {
    try {
        var Dir = Java.use('java.io.File');
        var d = Dir.$new(OUT);
        if (!d.exists()) d.mkdirs();
    } catch (e) {}
});

setImmediate(function () {
    try {
        dumpRange();
    } catch (e) {
        console.log('[-] dump error ' + e);
    }
});
