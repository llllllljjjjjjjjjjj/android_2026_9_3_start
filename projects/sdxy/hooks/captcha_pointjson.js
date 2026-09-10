// 捕获 App 端滑块验证码全链路（最强兜底）：
//  1) JavascriptApi.Y          —— checkResult(pointJson)
//  2) okhttp3 RealInterceptorChain —— 任何 OkHttp 请求（含 H5 经由其它 client 发的 captcha get/check）
//     -> 抓 get 响应(token+图URL) + check 请求(pointJson) + check 响应(result)
function sendEvent(kind, data) { try { send({ ev: kind, data: data }); } catch (e) {} }

function main() {
  Java.perform(function () {
    try {
      var JA = Java.use('com.huachenjie.base.dsbridge_webview.JavascriptApi');
      var Y = JA['Y'];
      if (Y) {
        Y.overloads.forEach(function (ov) {
          if (ov.argumentTypes.length === 2 && ov.argumentTypes[1].className.indexOf('CompletionHandler') >= 0) {
            ov.implementation = function (obj, ch) {
              try { sendEvent('bridge', obj ? obj.toString() : 'null'); } catch (e) {}
              return ov.call(this, obj, ch);
            };
          }
        });
        sendEvent('diag', 'hooked JavascriptApi.Y');
      } else sendEvent('diag', 'JavascriptApi no Y');
    } catch (e) { sendEvent('diag', 'err Y: ' + e); }

    try {
      var RC = Java.use('okhttp3.internal.http.RealInterceptorChain');
      RC.proceed.overloads.forEach(function (ov) {
        var at = ov.argumentTypes;
        if (at.length === 1 && at[0].className === 'okhttp3.Request') {
          ov.implementation = function (request) {
            var url = request.url().toString();
            var isCap = url.indexOf('captcha') >= 0;
            if (isCap) {
              sendEvent('net', 'METHOD=' + request.method() + ' URL=' + url);
              try {
                var body = request.body();
                if (body) {
                  var B = Java.use('okio.Buffer'); var b = B.$new();
                  body.writeTo(b); sendEvent('net_body', b.readUtf8());
                }
              } catch (e) { sendEvent('diag', 'reqbody e ' + e); }
            }
            var resp = this.proceed(request);
            if (isCap) {
              try {
                var rb = resp.body();
                if (rb) sendEvent('net_resp', resp.peekBody(65536).string());
              } catch (e) { sendEvent('diag', 'resp e ' + e); }
            }
            return resp;
          };
        }
      });
      sendEvent('diag', 'hooked RealInterceptorChain');
    } catch (e) { sendEvent('diag', 'err RC: ' + e); }

    try {
      var EC = Java.use('huachenjie.sdk.http.security.core.EncryptInterceptor');
      EC.intercept.implementation = function (chain) {
        var req = chain.request(); var url = req.url().toString();
        var isCap = url.indexOf('captcha') >= 0;
        if (isCap) {
          sendEvent('enc', 'URL=' + url);
          try { var b1 = req.body(); if (b1) { var B = Java.use('okio.Buffer'); var bb = B.$new(); b1.writeTo(bb); sendEvent('enc_body', bb.readUtf8()); } } catch (e) {}
        }
        var resp = this.intercept(chain);
        if (isCap) { try { if (resp.body()) sendEvent('enc_resp', resp.peekBody(65536).string()); } catch (e) {} }
        return resp;
      };
      sendEvent('diag', 'hooked EncryptInterceptor');
    } catch (e) { sendEvent('diag', 'err Enc: ' + e); }
  });
}
setImmediate(main);
