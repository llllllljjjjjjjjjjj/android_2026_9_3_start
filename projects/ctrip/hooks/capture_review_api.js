// Capture Ctrip SOA2 review/comment API requests (send-based)
Java.perform(function () {
    var seen = {};

    function b2s(bytes) {
        if (!bytes) return "";
        try {
            var S = Java.use("java.lang.String");
            var s = S.$new(bytes, "UTF-8");
            return String(s);
        } catch (e) { return "<bin " + bytes.length + ">"; }
    }

    function report(url, method, pipe, soa, enc, headers, body) {
        var bodyStr = String(body);
        var key = url + "|" + bodyStr.substring(0, 300);
        if (!url) return;
        if (seen[key]) return;
        seen[key] = 1;
        send({ t: "REQ", url: url, method: "" + method, pipe: "" + pipe, soa: soa, enc: enc, body: bodyStr });
    }

    // --- new path: CTHTTPClient.generateRequestDetail ---
    try {
        var C = Java.use("ctrip.android.httpv2.CTHTTPClient");
        C.generateRequestDetail.overloads.forEach(function (ov) {
            ov.implementation = function () {
                var rd = ov.apply(this, arguments);
                try {
                    report(rd.url.value, rd.method.value, rd.pipeType.value, rd.isSOARequest.value,
                        rd.enableEncrypt.value, rd.httpHeaders.value, b2s(rd.bodyBytes.value));
                } catch (e) { send({ t: "ERR", msg: "gen:" + e }); }
                return rd;
            };
        });
        send({ t: "OK", hook: "generateRequestDetail" });
    } catch (e) { send({ t: "ERR", msg: "gen hook fail:" + e }); }

    // --- old path + everything through OkHttp ---
    try {
        var B = Java.use("okhttp3.Request$Builder");
        B.build.implementation = function () {
            var r = this.build();
            try {
                var u = r.url().toString();
                var hs = r.headers();
                var hstr = "";
                for (var i = 0; i < hs.size(); i++) hstr += hs.name(i) + "=" + hs.value(i) + "; ";
                send({ t: "OKHTTP", url: u, method: r.method(), headers: hstr });
            } catch (e) { send({ t: "ERR", msg: "okhttp:" + e }); }
            return r;
        };
        send({ t: "OK", hook: "okhttp" });
    } catch (e) { send({ t: "ERR", msg: "okhttp hook fail:" + e }); }

    send({ t: "READY" });
});
