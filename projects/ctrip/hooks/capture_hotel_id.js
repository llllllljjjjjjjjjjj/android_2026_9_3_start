// 抓酒店搜索建议的 hotelID：hook recordTraceInfo + AutoCompleteHotelInformation 字段读取
Java.perform(function () {
    function s(o) {
        if (o === null || o === undefined) return "null";
        try { return String(o); } catch (e) { return "<obj>"; }
    }
    // 1) JSON.toJSONString 抓含 HotelID/海丽/嘉华 的输出
    try {
        var J = Java.use("com.alibaba.fastjson.JSON");
        J.toJSONString.overloads.forEach(function (ov) {
            ov.implementation = function () {
                var r = ov.apply(this, arguments);
                try {
                    var rs = s(r);
                    if (rs.indexOf("HotelID") >= 0 || rs.indexOf("海丽") >= 0 || rs.indexOf("嘉华") >= 0) {
                        send({ t: "TOJSON", out: rs });
                    }
                } catch (e) {}
                return r;
            };
        });
        send({ t: "OK", hook: "toJSONString" });
    } catch (e) { send({ t: "ERR", msg: "toJSON:" + e }); }
    // 2) hook recordTraceInfo(AutoCompleteHotelInformation, String)
    try {
        var C = Java.use("ctrip.android.hotel.viewmodel.hotel.HotelInquireMainCacheBean");
        C.recordTraceInfo.overloads.forEach(function (ov) {
            ov.implementation = function () {
                try {
                    var info = arguments[0];
                    if (info) {
                        send({ t: "HOTEL", id: info.hotelID.value, zone: info.zoneName.value, point: info.customerPoint.value });
                    }
                } catch (e) { send({ t: "ERR", msg: "recordTrace:" + e }); }
                return ov.apply(this, arguments);
            };
        });
        send({ t: "OK", hook: "recordTraceInfo" });
    } catch (e) { send({ t: "ERR", msg: "recordTraceInfo:" + e }); }
});
