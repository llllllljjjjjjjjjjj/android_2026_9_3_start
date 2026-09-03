# search_body_probe3.py — deflate/compress2 探针：抓 gzip 压缩前的明文 body
# 原理：搜索请求 body 是 protobuf，上传前经 zlib deflate 压缩。
# hook deflate(strm, flush)：z_stream.next_in = 压缩前明文。
# 输入含 "meishi"/"search"/"general"/"keyword" 时 dump 完整明文 + backtrace。
import frida, sys, time

DEVICE = '127.0.0.1:27042'

JS = r'''
var hits = 0;

function dumpHex(ptr, n) {
  var s = "";
  for (var i = 0; i < n; i++) s += ("0" + ptr.add(i).readU8().toString(16)).slice(-2) + (i % 16 === 15 ? "\n" : " ");
  return s;
}

function checkBuf(ptr, size, where) {
  if (size < 4 || size > 131072) return false;
  var probe;
  try { probe = ptr.readUtf8String(Math.min(size, 2048)); } catch (e) { return false; }
  if (!/meishi|search_keyword|general\/|keyword|sug|billboard|search_id/i.test(probe)) return false;
  hits++;
  send("[DEF-HIT] " + where + " size=" + size + "\n" + probe.slice(0, 1200));
  var n = Math.min(size, 8192);
  try { send("[DEF-HEX]\n" + dumpHex(ptr, n)); } catch (e) { send("[DEF-HEX] err " + e.message); }
  try {
    var bt = Thread.backtrace(this.context, Backtracer.ACCURATE).slice(0, 14).map(function (a) {
      var m = Process.findModuleByAddress(a);
      return a + (m ? " " + m.name + "+0x" + a.sub(m.base).toString(16) : "");
    });
    send("[DEF-BT] " + bt.join(" | "));
  } catch (e) { send("[DEF-BT] err " + e.message); }
  return true;
}

function hookDeflate(addr, modName) {
  Interceptor.attach(addr, {
    onEnter: function (args) {
      try {
        // z_stream: 0x00 next_in, 0x08 avail_in
        var nin = args[0].readPointer();
        var ain = args[0].add(8).readU32();
        this.nin = nin; this.ain = ain; this.where = modName + ":deflate";
      } catch (e) {}
    },
    onLeave: function () {
      if (this.nin) try { checkBuf(this.nin, this.ain, this.where); } catch (e) {}
    }
  });
}

function hookCompress2(addr, modName) {
  Interceptor.attach(addr, {
    onEnter: function (args) {
      // compress2(dest, destLen, source, sourceLen, level)
      try { checkBuf(args[2], args[3].toInt32(), modName + ":compress2"); } catch (e) {}
    }
  });
}

var seen = {};
Process.enumerateModules().forEach(function (m) {
  if (!/libz|borg|sscronet|nss|metasec|libcore|tob|keva/i.test(m.name)) return;
  try {
    m.enumerateExports().forEach(function (e) {
      var key = e.address.toString();
      if (seen[key]) return;
      seen[key] = true;
      if (e.name === "deflate") { hookDeflate(e.address, m.name); send("[ARM] deflate " + m.name + " @ " + e.address); }
      else if (e.name === "deflateInit2_") { send("[INFO] deflateInit2_ " + m.name + " @ " + e.address); }
      else if (e.name === "compress2") { hookCompress2(e.address, m.name); send("[ARM] compress2 " + m.name + " @ " + e.address); }
      else if (e.name === "compress") { hookCompress2(e.address, m.name); send("[ARM] compress " + m.name + " @ " + e.address); }
    });
  } catch (e) {}
});
send("[DONE] armed. hits=" + hits);
'''

def main():
    dev = frida.get_device_manager().add_remote_device(DEVICE)
    target = None
    for p in dev.enumerate_processes():
        if p.name in ('抖音', 'com.ss.android.ugc.aweme'):
            target = p; break
    if not target:
        print('抖音进程未找到'); return
    print('attach pid=%d' % target.pid)
    s = dev.attach(target.pid)
    sc = s.create_script(JS)
    sc.on('message', lambda m, d: print('[msg]', m.get('payload', '') if isinstance(m.get('payload', ''), str) else str(m)[:200]))
    sc.load()
    print('探针已注入，观察 90s（期间请在真机触发一次搜索）……')
    time.sleep(90)

if __name__ == '__main__':
    main()
