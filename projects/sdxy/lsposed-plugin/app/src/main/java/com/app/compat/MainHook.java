package com.app.compat;

import android.app.Application;
import android.os.Bundle;

import java.io.File;
import java.security.MessageDigest;
import java.util.List;
import java.util.Map;

import de.robv.android.xposed.IXposedHookLoadPackage;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XposedHelpers;
import de.robv.android.xposed.callbacks.XC_LoadPackage;

/**
 * 闪动校园阳光跑数据只读记录器（最小风险版）。
 *
 * 风险最小化设计（相对初版的 11 hook + loadClass 兜底）：
 *  1. 只 hook 2~3 个「直接类」方法（base.apk 未加密，用 app classLoader 即可找到）：
 *     - K.b2s               → runImgRecord 图片派生值（唯一 native 未知项）
 *     - ApiDataComponent.b0 → strideMap 内部 key
 *     - DataComponent.h1    → finish body（交叉验证，可选）
 *  2. 不再 hook 任何加密类（c23/mp8/qf7/a15/ParamsInterceptor）——它们要验证的
 *     signKey/encKey/MD5/上传格式均已静态还原 + 字节级验证，无需动态重复。
 *  3. 彻底去掉 ClassLoader.loadClass 兜底（易盾最易察觉的敏感 hook 点）。
 *  4. hook 时机延迟：不在 Application.attach（易盾启动检测期），改为
 *     Application.onCreate（初始化完成）+ ReadyActivity.onCreate（跑步准备页）两轮。
 *  5. 只读 hook：绝不 setResult/setArg，App 行为与数据流不变。
 */
public class MainHook implements IXposedHookLoadPackage {

    private static final String TARGET = "com.huachenjie.shandong_school";

    @Override
    public void handleLoadPackage(XC_LoadPackage.LoadPackageParam lp) {
        if (!TARGET.equals(lp.packageName)) {
            return;
        }

        // 锚点 1：Application.onCreate 之后（易盾启动检测期已过）
        try {
            XposedHelpers.findAndHookMethod(Application.class, "onCreate",
                    new XC_MethodHook() {
                        @Override
                        protected void afterHookedMethod(MethodHookParam param) {
                            initLog((Application) param.thisObject);
                            hookCore(lp.classLoader);
                        }
                    });
        } catch (Throwable t) {
            LogUtil.log("ERR hook Application.onCreate: " + t);
        }

        // 锚点 2：跑步准备页（真实跑步必经），兜底补 hook
        try {
            XposedHelpers.findAndHookMethod(
                    "com.huachenjie.running.page.activities_run.ReadyActivity",
                    lp.classLoader, "onCreate", Bundle.class,
                    new XC_MethodHook() {
                        @Override
                        protected void afterHookedMethod(MethodHookParam param) {
                            hookCore(lp.classLoader);
                        }
                    });
        } catch (Throwable t) {
            LogUtil.log("ERR hook ReadyActivity.onCreate: " + t);
        }
    }

    private void initLog(Application app) {
        try {
            File base = app.getExternalFilesDir(null);
            if (base == null) {
                base = app.getFilesDir();
            }
            LogUtil.init(new File(base, "hook"));
        } catch (Throwable ignored) {
        }
    }

    private void hookCore(ClassLoader cl) {
        hookK(cl);
        hookApiDataComponent(cl);
        hookDataComponent(cl);
    }

    // 1. K.b2s(byte[], int) —— runImgRecord 图片派生值（native）
    private void hookK(ClassLoader cl) {
        tryHook(cl, "com.huachenjie.c.K", "b2s",
                new Class<?>[]{byte[].class, int.class}, new XC_MethodHook() {
                    @Override
                    protected void beforeHookedMethod(MethodHookParam p) {
                        byte[] data = (byte[]) p.args[0];
                        int mode = (Integer) p.args[1];
                        LogUtil.log("K.b2s IN len=" + (data == null ? -1 : data.length)
                                + " mode=" + mode
                                + " sha256=" + sha256(data)
                                + " head=" + hexHead(data, 32));
                    }

                    @Override
                    protected void afterHookedMethod(MethodHookParam p) {
                        LogUtil.log("K.b2s OUT=" + p.getResult());
                    }
                });
    }

    // 2. ApiDataComponent.b0(Map,int,String,ValueCallBack) —— strideMap 内部 key
    private void hookApiDataComponent(ClassLoader cl) {
        Class<?> vcb = null;
        try {
            vcb = XposedHelpers.findClass("com.huachenjie.common.callback.ValueCallBack", cl);
        } catch (Throwable ignored) {
        }
        if (vcb == null) {
            return;
        }
        tryHook(cl, "com.huachenjie.running.service.ApiDataComponent", "b0",
                new Class<?>[]{Map.class, int.class, String.class, vcb},
                new XC_MethodHook() {
                    @Override
                    protected void beforeHookedMethod(MethodHookParam p) {
                        LogUtil.log("ApiDataComponent.b0 strideList=" + deep(p.args[0])
                                + " strideInterval=" + p.args[1]
                                + " runRecordCode=" + p.args[2]);
                    }
                });
    }

    // 3. DataComponent.h1(boolean,int) —— finish body（交叉验证）
    private void hookDataComponent(ClassLoader cl) {
        tryHook(cl, "com.huachenjie.running.service.DataComponent", "h1",
                new Class<?>[]{boolean.class, int.class}, new XC_MethodHook() {
                    @Override
                    protected void beforeHookedMethod(MethodHookParam p) {
                        LogUtil.log("DataComponent.h1 IN isValid=" + p.args[0]
                                + " cheatType=" + p.args[1]);
                    }

                    @Override
                    protected void afterHookedMethod(MethodHookParam p) {
                        LogUtil.log("DataComponent.h1 OUT=" + deep(p.getResult()));
                    }
                });
    }

    // ------------------------------------------------------------------
    private boolean tryHook(ClassLoader cl, String className, String methodName,
                            Class<?>[] paramTypes, XC_MethodHook cb) {
        try {
            Class<?> c = XposedHelpers.findClass(className, cl);
            Object[] args = new Object[paramTypes.length + 1];
            System.arraycopy(paramTypes, 0, args, 0, paramTypes.length);
            args[paramTypes.length] = cb;
            XposedHelpers.findAndHookMethod(c, methodName, args);
            LogUtil.log("HOOKED " + className + "." + methodName);
            return true;
        } catch (Throwable t) {
            return false;
        }
    }

    // ------------------------------------------------------------------
    private static String sha256(byte[] b) {
        if (b == null) {
            return "null";
        }
        try {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] d = md.digest(b);
            StringBuilder sb = new StringBuilder();
            for (byte x : d) {
                sb.append(String.format("%02x", x & 0xff));
            }
            return sb.toString();
        } catch (Throwable t) {
            return "err";
        }
    }

    private static String hexHead(byte[] b, int n) {
        if (b == null) {
            return "null";
        }
        int m = Math.min(n, b.length);
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < m; i++) {
            sb.append(String.format("%02x", b[i] & 0xff));
        }
        return sb.toString();
    }

    private static String truncate(String s, int max) {
        if (s == null) {
            return "null";
        }
        return s.length() <= max ? s : s.substring(0, max) + "...";
    }

    private static String deep(Object o) {
        return deep(o, 0);
    }

    private static String deep(Object o, int depth) {
        if (o == null) {
            return "null";
        }
        if (depth > 3) {
            return "...";
        }
        if (o instanceof byte[]) {
            byte[] b = (byte[]) o;
            return "[bytes len=" + b.length + " sha256=" + sha256(b) + " head=" + hexHead(b, 32) + "]";
        }
        if (o instanceof Map) {
            Map<?, ?> m = (Map<?, ?>) o;
            StringBuilder sb = new StringBuilder("{");
            int i = 0;
            for (Map.Entry<?, ?> e : m.entrySet()) {
                if (i++ > 0) {
                    sb.append(", ");
                }
                sb.append(String.valueOf(e.getKey())).append("=").append(deep(e.getValue(), depth + 1));
                if (sb.length() > 4000) {
                    sb.append("...TRUNC");
                    break;
                }
            }
            sb.append("}");
            return sb.toString();
        }
        if (o instanceof List) {
            List<?> l = (List<?>) o;
            StringBuilder sb = new StringBuilder("[size=").append(l.size()).append("]{");
            int n = Math.min(l.size(), 40);
            for (int i = 0; i < n; i++) {
                if (i > 0) {
                    sb.append(", ");
                }
                sb.append(deep(l.get(i), depth + 1));
                if (sb.length() > 4000) {
                    sb.append("...TRUNC");
                    break;
                }
            }
            sb.append("}");
            return sb.toString();
        }
        return truncate(String.valueOf(o), 600);
    }
}
