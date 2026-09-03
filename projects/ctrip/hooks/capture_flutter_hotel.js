// 抓 Flutter MethodChannel 调用，定位酒店列表/详情的 hotelId
Java.perform(function () {
    function s(o) {
        if (o === null || o === undefined) return "null";
        try { return String(o); } catch (e) { return "<obj>"; }
    }
    try {
        var MC = Java.use("io.flutter.plugin.common.MethodChannel");
        MC.invokeMethod.overloads.forEach(function (ov) {
            ov.implementation = function () {
                try {
                    var m = arguments[0];
                    var a = arguments.length > 1 ? arguments[1] : null;
                    var ms = s(m), as = s(a);
                    if (as.indexOf("otel") >= 0 || as.indexOf("hotelId") >= 0 || ms.indexOf("otel") >= 0) {
                        send({ t: "FLUTTER", method: ms, args: as });
                    }
                } catch (e) {}
                return ov.apply(this, arguments);
            };
        });
        send({ t: "OK", n: MC.invokeMethod.overloads.length });
    } catch (e) { send({ t: "ERR", msg: "" + e }); }
});
