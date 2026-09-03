// 抓所有 soa2 请求（URL + body）+ 响应（fastjson parseObject 反序列化的对象），用于定位酒店搜索 hotelID
Java.perform(function () {
    function b2s(bytes) {
        if (!bytes) return "null";
        try { return String(Java.use("java.lang.String").$new(bytes, "UTF-8")); } catch (e) { return "<bin>"; }
    }
    // 请求：generateRequestDetail 抓 URL + body
    try {
        var C = Java.use("ctrip.android.httpv2.CTHTTPClient");
        C.generateRequestDetail.overloads.forEach(function (ov) {
            ov.implementation = function () {
                var rd = ov.apply(this, arguments);
                try {
                    var u = rd.url.value;
                    if (u.indexOf("soa2") >= 0) {
                        send({ t: "REQ", url: u, body: b2s(rd.bodyBytes.value) });
                    }
                } catch (e) {}
                return rd;
            };
        });
        send({ t: "OK", hook: "gen" });
    } catch (e) { send({ t: "ERR", msg: "gen:" + e }); }
    // 响应：fastjson parseObject 抓含 hotel/酒店 的反序列化字符串
    try {
        var J = Java.use("com.alibaba.fastjson.JSON");
        J.parseObject.overloads.forEach(function (ov) {
            ov.implementation = function () {
                try {
                    var a0 = arguments[0];
                    var s = String(a0);
                    if (s && (s.indexOf("otel") >= 0 || s.indexOf("Hotel") >= 0)) {
                        send({ t: "RESP", body: s });
                    }
                } catch (e) {}
                return ov.apply(this, arguments);
            };
        });
        send({ t: "OK", hook: "parseObject" });
    } catch (e) { send({ t: "ERR", msg: "parseObject:" + e }); }
    send({ t: "READY" });
});
