'use strict';
/*
 * 动态探测：attach 到运行中的闪动校园主进程，验证：
 *  1. 业务类是否已解密加载（c23/K/DataComponent/mp8/qf7）
 *  2. c23.d()/c23.b() 实际值（验证 signKey/encKey 静态结论）
 *  3. 当前登录态 token 是否可读（na9）
 */
rpc.exports = {
    probe: function () {
        var out = {};
        Java.perform(function () {
            try {
                var loaded = Java.enumerateLoadedClassesSync();
                var targets = [
                    'com.zj.widget.c23',
                    'com.zj.widget.cq',
                    'com.zj.widget.k14',
                    'com.zj.widget.r01',
                    'com.huachenjie.c.K',
                    'com.huachenjie.running.service.DataComponent',
                    'com.huachenjie.running.service.ApiDataComponent',
                    'com.zj.widget.mp8',
                    'com.zj.widget.qf7',
                    'com.zj.widget.hp8',
                    'com.zj.widget.a15',
                    'com.zj.widget.na9'
                ];
                out.loaded = {};
                for (var i = 0; i < targets.length; i++) {
                    out.loaded[targets[i]] = loaded.indexOf(targets[i]) >= 0;
                }
                out.loadedCount = loaded.length;
            } catch (e) {
                out.loadedErr = String(e);
            }

            // c23 静态 getter
            try {
                var c23 = Java.use('com.zj.widget.c23');
                out.c23_d = c23.d() == null ? null : String(c23.d());
                out.c23_b = c23.b() == null ? null : String(c23.b());
                out.c23_a = c23.a() == null ? null : String(c23.a());
            } catch (e) {
                out.c23Err = String(e);
            }

            // na9 token
            try {
                var na9 = Java.use('com.zj.widget.na9');
                var inst = na9.c();
                if (inst != null) {
                    try { out.token = String(inst.getToken()); } catch (e2) { out.tokenErr = String(e2); }
                    try { out.satoken = String(inst.getSatoken()); } catch (e3) { out.satokenErr = String(e3); }
                    try { out.userId = String(inst.getUserId()); } catch (e4) { out.userIdErr = String(e4); }
                }
            } catch (e) {
                out.na9Err = String(e);
            }

            // r01 常量
            try {
                var r01 = Java.use('com.zj.widget.r01');
                out.r01_e = String(r01.e.value);
                out.r01_f = String(r01.f.value);
            } catch (e) {
                out.r01Err = String(e);
            }
        });
        return out;
    }
};
