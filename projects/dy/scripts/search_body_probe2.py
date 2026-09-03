# search_body_probe2.py — 探针：hook Cronet_UploadDataProvider_Read 抓 POST body
# Read 签名(Cronet C API): void read(provider, upload_data_sink, buffer)
# buffer 数据经 Cronet_Buffer_GetData / Cronet_Buffer_GetSize 读取
import frida, sys, time

DEVICE = '127.0.0.1:27042'

def main():
    dev = frida.get_device_manager().add_remote_device(DEVICE)
    target = None
    for p in dev.enumerate_processes():
        if p.name == '抖音' or p.name == 'com.ss.android.ugc.aweme':
            target = p; break
    if not target:
        print('抖音进程未找到'); return
    s = dev.attach(target.pid)
    sc = s.create_script(r'''
var m = Process.findModuleByName("libsscronet.so");
if (!m) { send("libsscronet not loaded"); }
else {
  // 先枚举 buffer 相关导出
  var buf = [];
  m.enumerateExports().forEach(function(e){
    if (/Buffer_Get/i.test(e.name)) buf.push(e.name + " @ 0x" + e.address.sub(m.base).toString(16));
  });
  send("buffer exports:\n" + buf.join("\n"));

  // hook Cronet_UploadDataProvider_Read @ 0x27765c
  var readAddr = m.base.add(0x27765c);
  var getData = null, getSize = null;
  m.enumerateExports().forEach(function(e){
    if (e.name === "Cronet_Buffer_GetData") getData = e.address;
    if (e.name === "Cronet_Buffer_GetSize") getSize = e.address;
  });
  send("getData=" + getData + " getSize=" + getSize);
  var fnGetData = getData ? new NativeFunction(getData, 'pointer', ['pointer']) : null;
  var fnGetSize = getSize ? new NativeFunction(getSize, 'uint64', ['pointer']) : null;

  Interceptor.attach(readAddr, {
    onEnter: function (args) {
      this.sink = args[1];
      this.buf = args[2];
      try {
        if (fnGetData && this.buf && !this.buf.isNull()) {
          var data = fnGetData(this.buf);
          var size = fnGetSize ? Number(fnGetSize(this.buf)) : 0;
          if (!data.isNull() && size > 0 && size < 4096) {
            var txt = data.readUtf8String(size);
            if (/search|keyword|meishi/i.test(txt) || true) {
              send("[BODY] size=" + size + "\n" + txt);
            }
          } else {
            send("[BODY-ptr] data=" + data + " size=" + size);
          }
        } else {
          send("[BODY] no getData, buf=" + this.buf);
        }
      } catch (e) { send("[BODY] err " + e.message); }
    }
  });
  send("armed Read hook @ libsscronet+0x27765c");
}
''')
    sc.on('message', lambda m, d: print('[msg]', str(m.get('payload', ''))[:800]))
    sc.load()
    print('探针已注入，等 60s 观察 body 读取……')
    time.sleep(60)

if __name__ == '__main__':
    main()
