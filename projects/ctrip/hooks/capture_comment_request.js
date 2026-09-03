// 抓 RN 传给原生层的原始 body（fastjson JSON.parseObject 所有 overload）
Java.perform(function () {
    try {
        var JSON = Java.use("com.alibaba.fastjson.JSON");
        JSON.parseObject.overloads.forEach(function (ov) {
            ov.implementation = function () {
                try {
                    var a0 = arguments[0];
                    var str = String(a0);
                    if (str && (str.indexOf("hotelId") >= 0 || str.indexOf("HotelId") >= 0 || str.indexOf("omment") >= 0)) {
                        send({ t: "RAW", body: str });
                    }
                } catch (e) {}
                return ov.apply(this, arguments);
            };
        });
        send({ t: "OK", n: JSON.parseObject.overloads.length });
    } catch (e) { send({ t: "ERR", msg: "" + e }); }
});
