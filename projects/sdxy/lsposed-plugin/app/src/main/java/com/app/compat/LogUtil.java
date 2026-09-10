package com.app.compat;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/**
 * 线程安全的落盘日志。写在目标 App 外部 files 目录下，adb pull 无需 root。
 * 文件名用 trace_<pid>.log，不含敏感词。
 */
public final class LogUtil {

    private static final Object LOCK = new Object();
    private static final SimpleDateFormat TS =
            new SimpleDateFormat("MM-dd HH:mm:ss.SSS", Locale.US);
    private static File logFile = null;

    private LogUtil() {
    }

    public static synchronized void init(File dir) {
        if (logFile != null || dir == null) {
            return;
        }
        try {
            if (!dir.exists()) {
                dir.mkdirs();
            }
            logFile = new File(dir, "trace_" + android.os.Process.myPid() + ".log");
            raw("===== session start pid=" + android.os.Process.myPid() + " =====");
        } catch (Throwable ignored) {
        }
    }

    public static void log(String msg) {
        raw(msg);
    }

    private static void raw(String msg) {
        synchronized (LOCK) {
            if (logFile == null) {
                return;
            }
            FileWriter fw = null;
            try {
                fw = new FileWriter(logFile, true);
                fw.write("[" + TS.format(new Date()) + "] " + msg + "\n");
                fw.flush();
            } catch (IOException ignored) {
            } finally {
                if (fw != null) {
                    try {
                        fw.close();
                    } catch (IOException ignored) {
                    }
                }
            }
        }
    }
}
