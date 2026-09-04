'use strict';
/*
 * 读登录态：调用 na9.c() 返回 CommonUserInfo（含 token/satoken/userId/schoolCode）。
 */
rpc.exports = {
    dump: function () {
        var out = {};
        Java.perform(function () {
            try {
                var loaders = Java.enumerateClassLoadersSync();
                var na9cls = null;
                for (var i = 0; i < loaders.length; i++) {
                    try {
                        var c = loaders[i].loadClass('com.zj.widget.na9');
                        if (c != null) { na9cls = c; break; }
                    } catch (e) {}
                }
                if (na9cls == null) { out.error = 'na9 not loadable'; return; }

                // 调静态方法 c() 返回 CommonUserInfo
                var cm = na9cls.getDeclaredMethod('c');
                cm.setAccessible(true);
                var info = cm.invoke(null);

                // 读字段（getter 反射）
                function readGetter(obj, name) {
                    try {
                        var m = obj.getClass().getDeclaredMethod(name);
                        m.setAccessible(true);
                        var v = m.invoke(obj);
                        return v == null ? null : String(v);
                    } catch (e) { return 'ERR:' + e.message; }
                }
                out.userId = readGetter(info, 'getUserId');
                out.token = readGetter(info, 'getToken');
                out.satoken = readGetter(info, 'getSatoken');
                out.schoolCode = readGetter(info, 'getSchoolCode');
                out.schoolName = readGetter(info, 'getSchoolName');
                out.studentNumber = readGetter(info, 'getStudentNumber');
                out.userName = readGetter(info, 'getUserName');
                out.phone = readGetter(info, 'getPhone');
            } catch (e) {
                out.error = String(e);
            }
        });
        return out;
    }
};
