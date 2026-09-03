// Ctrip x-payload-source 在线签名 oracle（策略 E：Frida RPC）
// 每个 RPC 方法用 Java.perform 包裹 + try-catch 防崩溃
var SU = null;
var JString = null;

function withJava(fn) {
    var out = null;
    Java.perform(function () {
        try {
            if (!SU) { SU = Java.use("ctrip.android.security.SecurityUtil"); }
            if (!JString) { JString = Java.use("java.lang.String"); }
            out = fn();
        } catch (e) {
            out = "ERR:" + e;
        }
    });
    return out;
}

rpc.exports = {
    sign: function (md5hex) {
        return withJava(function () {
            var b = JString.$new("" + md5hex).getBytes("UTF-8");
            return SU.getInstance().bnSimpleSign(b, "getdata");
        });
    },
    // 批量签名：一次 RPC 拿多个签名，避免连续 RPC 触发反检测
    batchSign: function (md5list) {
        return withJava(function () {
            var out = [];
            for (var i = 0; i < md5list.length; i++) {
                var b = JString.$new("" + md5list[i]).getBytes("UTF-8");
                out.push(SU.getInstance().bnSimpleSign(b, "getdata"));
            }
            return out;
        });
    },
    strongSign: function (md5hex) {
        return withJava(function () {
            var b = JString.$new("" + md5hex).getBytes("UTF-8");
            return SU.getInstance().bnStrongSign(b, "getdata");
        });
    },
    getToken: function () { return withJava(function () { return SU.getInstance().bnGetToken(); }); },
    getToken2: function () { return withJava(function () { return SU.getInstance().bnGetToken2(); }); },
    getLabelV2: function () { return withJava(function () { return SU.getInstance().bnGetLabelV2(); }); },
    getAppBootTime: function () { return withJava(function () { return SU.getInstance().getAppBootTime(); }); }
};

setTimeout(function () { send({ t: "RPC_READY" }); }, 500);
