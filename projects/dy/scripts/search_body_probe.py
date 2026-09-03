# search_body_probe.py — 枚举 libsscronet 上传/body 相关导出符号（一次性探针）
import frida, sys, time

DEVICE = '127.0.0.1:27042'

def main():
    dev = frida.get_device_manager().add_remote_device(DEVICE)
    procs = dev.enumerate_processes()
    target = None
    for p in procs:
        if p.name == '抖音' or p.name == 'com.ss.android.ugc.aweme':
            target = p
            break
    if not target:
        print('抖音进程未找到'); return
    print('attach pid=%d name=%s' % (target.pid, target.name))
    s = dev.attach(target.pid)
    sc = s.create_script(r'''
var m = Process.findModuleByName("libsscronet.so");
if (!m) { send("libsscronet.so not loaded"); }
else {
  var out = [];
  var re = /upload|Upload|body|Body|read|Read/i;
  m.enumerateExports().forEach(function(e){
    if (re.test(e.name)) out.push(e.name + " @ 0x" + e.address.sub(m.base).toString(16));
  });
  send("total exports: " + m.enumerateExports().length);
  send("matched: " + out.length);
  send(out.join("\n"));
}
''')
    sc.on('message', lambda m, d: print('[msg]', m.get('payload', '') if isinstance(m.get('payload', ''), str) else str(m)[:500]))
    sc.load()
    time.sleep(5)

if __name__ == '__main__':
    main()
