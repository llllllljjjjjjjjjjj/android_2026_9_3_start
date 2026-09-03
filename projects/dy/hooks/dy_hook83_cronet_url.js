// dy_hook83_cronet_url.js — 枚举 libsscronet Cronet URL 层导出并抓实时请求 URL
//
// 目标：播放器拉流直链（douyinvod/douyinstatic）不经过 metasec 签名回调，
// 只能从 Cronet 请求构建层抓。先枚举导出，再对候选函数 hook 打印 URL。
//
// 输出：
//   [EXPORT] <name> @ <addr>       枚举到的 Cronet_* 导出
//   [CURL] <url>                   从候选函数参数中抓到的实时请求 URL

var cronet = null;

function enumerate() {
  cronet = Process.findModuleByName("libsscronet.so");
  if (!cronet) return;
  cronet.enumerateExports().forEach(function (e) {
    if (/UrlRequest|Request_|_Request/i.test(e.name)) {
      console.log("[EXPORT] " + e.name + " @ " + e.address);
    }
  });
  console.log("[hook83] export enum done");
}

enumerate();
setInterval(enumerate, 4000);
console.log("[hook83] loaded");
