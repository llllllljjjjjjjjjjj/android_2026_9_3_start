# 不混淆入口类，否则 LSPosed 找不到 xposed_init 指向的类
-keep class com.app.compat.MainHook { *; }
-keep class com.app.compat.LogUtil { *; }
