// Minimal injection test for Ctrip
Java.perform(function () {
    send({ t: "JAVA_READY", vm: Java.available });
    try {
        var C = Java.use("ctrip.android.httpv2.CTHTTPClient");
        send({ t: "CLASS_FOUND", cls: "CTHTTPClient", methods: C.class.getDeclaredMethods().length });
    } catch (e) {
        send({ t: "CLASS_MISS", err: "" + e });
    }
    try {
        var Ok = Java.use("okhttp3.OkHttpClient");
        send({ t: "OKHTTP_FOUND" });
    } catch (e) {
        send({ t: "OKHTTP_MISS", err: "" + e });
    }
});
