// Capture SecurityUtil sign functions (input/output pairs)
Java.perform(function () {
    function bytes2hex(b) {
        if (!b) return "null";
        try {
            var s = Java.use("java.lang.String").$new(b, "UTF-8");
            return String(s);
        } catch (e) { return "<bin " + b.length + ">"; }
    }
    function hx(js) {
        try {
            var B = Java.use("[B");
            return "" + js;
        } catch (e) { return "" + js; }
    }

    var SU = Java.use("ctrip.android.security.SecurityUtil");
    var target = "ctrip.android.security.SecurityUtil";

    // hook public bnSimpleSign(byte[], String)
    try {
        SU.bnSimpleSign.overload("[B", "java.lang.String").implementation = function (b, s) {
            var r = this.bnSimpleSign(b, s);
            send({ t: "SIGN", fn: "bnSimpleSign", in_str: String(s), in_bytes: bytes2hex(b), out: String(r) });
            return r;
        };
        send({ t: "OK", hook: "bnSimpleSign" });
    } catch (e) { send({ t: "ERR", msg: "bnSimpleSign: " + e }); }

    try {
        SU.bnStrongSign.overload("[B", "java.lang.String").implementation = function (b, s) {
            var r = this.bnStrongSign(b, s);
            send({ t: "SIGN", fn: "bnStrongSign", in_str: String(s), in_bytes: bytes2hex(b), out: String(r) });
            return r;
        };
        send({ t: "OK", hook: "bnStrongSign" });
    } catch (e) { send({ t: "ERR", msg: "bnStrongSign: " + e }); }

    // hook token/label getters
    ["bnGetToken", "bnGetToken2", "bnGetLabelV2", "getAppBootTime"].forEach(function (n) {
        try {
            SU[n].overload().implementation = function () {
                var r = this[n]();
                send({ t: "TOKEN", fn: n, out: String(r) });
                return r;
            };
            send({ t: "OK", hook: n });
        } catch (e) { send({ t: "ERR", msg: n + ": " + e }); }
    });

    send({ t: "READY" });
});
