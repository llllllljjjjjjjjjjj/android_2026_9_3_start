'use strict';
/*
 * 在闪动校园进程内部验证：
 *  1. su 文件是否可见（Shamiko 是否隐藏了 root）
 *  2. Magisk/LSPosed/插件包是否可见（HMA 是否生效）
 */
rpc.exports = {
    check: function () {
        var out = {};
        Java.perform(function () {
            var File = Java.use('java.io.File');
            out.files = {};
            var paths = [
                '/sbin/su', '/system/xbin/su', '/system/bin/su',
                '/data/adb/magisk', '/data/adb/modules', '/data/local/tmp'
            ];
            for (var i = 0; i < paths.length; i++) {
                try {
                    out.files[paths[i]] = File.$new(paths[i]).exists();
                } catch (e) {
                    out.files[paths[i]] = 'ERR:' + e;
                }
            }

            // HMA 验证：PackageManager 能否看到逆向工具包
            try {
                var app = Java.use('android.app.ActivityThread').currentApplication();
                var pm = app.getPackageManager();
                var pkgs = [
                    'com.topjohnwu.magisk',
                    'io.github.lsposed.manager',
                    'com.app.compat',
                    'com.tsng.hidemyapplist',
                    'com.junge.algorithmAide'
                ];
                out.pkg_visibility = {};
                for (var j = 0; j < pkgs.length; j++) {
                    try {
                        pm.getPackageInfo(pkgs[j], 0);
                        out.pkg_visibility[pkgs[j]] = 'VISIBLE';
                    } catch (e) {
                        out.pkg_visibility[pkgs[j]] = 'HIDDEN';
                    }
                }
            } catch (e) {
                out.pm_err = String(e);
            }
        });
        return out;
    }
};
