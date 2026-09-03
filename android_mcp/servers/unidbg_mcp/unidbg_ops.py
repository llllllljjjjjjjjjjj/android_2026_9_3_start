# -*- coding: utf-8 -*-
"""unidbg_ops — unidbg 离线 SO 参数生成（JPype 进程内调 jar）。

负责：
  1. lazy 启动 JVM（第一次工具调用时，在 MCP 单 worker 线程上），加载 shade 后的 fat jar
  2. 进程内直调 Java 补环境类，生成 SO 参数（签名/指纹/token/加密参数等）

🔴 前置（见 protocol-signature-reverser SKILL Phase 6.1）：
  - Java 层必须先用 main() 字节级验证跑通 → 才打 jar（jar 不修补环境失败）
  - fat jar 必须 maven-shade 打全 unidbg 依赖，否则 ClassNotFoundError
  - 0.9.9 老框架要 JDK 8：用 UNIDBG_JAVA_HOME 指向 JDK 8 根目录

环境变量覆盖（§7.4 风格）：
  UNIDBG_JAR         → 覆盖 fat jar 路径（默认 tools/unidbg-boot-server/sign-generator-fat.jar）
  UNIDBG_JAVA_HOME   → 指定 JDK 根目录（0.9.9 用 JDK 8）；缺省走 jpype 默认 JVM
"""
from __future__ import annotations

import os
import threading
from pathlib import Path

# 项目根：unidbg_ops.py 位于 android_mcp/servers/unidbg_mcp/，parents[3] = 项目根
ROOT = Path(__file__).resolve().parents[3]

# 默认 fat jar 路径（相对项目根）。shade 打全 unidbg 依赖后的产物
# （pom.xml 已配 maven-shade-plugin，`mvn package` 产出 *-shaded.jar）。
JAR_DEFAULT = "tools/unidbg-boot-server/target/unidbg-boot-server-0.0.1-SNAPSHOT-shaded.jar"

_JVM_LOCK = threading.Lock()
_JVM_UP = False
_Generator = None  # JPype 导入的 Java 补环境类句柄

# 补环境类全限定名 + 生成方法签名。工程已内置 SignGenerator（service 包）占位模板，
# 按真实目标 so 改写 TTEncryptService 后，改这里指向你的类即可。
_GENERATOR_CLASS = "com.anjia.unidbgserver.service.SignGenerator"
_GENERATOR_METHOD = "generate"


def _resolve_jar() -> Path:
    jar = os.environ.get("UNIDBG_JAR") or JAR_DEFAULT
    p = Path(jar)
    if not p.is_absolute():
        p = ROOT / p
    return p


def _resolve_jvm_path():
    """返回 jvm.dll 路径；UNIDBG_JAVA_HOME 未设时返回 None（jpype 默认 JVM 兜底）。"""
    java_home = os.environ.get("UNIDBG_JAVA_HOME")
    if not java_home:
        return None
    home = Path(java_home)
    for rel in ("bin/server/jvm.dll", "jre/bin/server/jvm.dll", "bin/client/jvm.dll"):
        cand = home / rel
        if cand.exists():
            return str(cand)
    return str(home / "bin" / "server" / "jvm.dll")


def _ensure_jvm():
    """lazy 启动 JVM 并导入补环境类；同一进程只启动一次。

    MCP 框架（StdioMcpServer）用单 worker 线程串行调用工具，
    第一次 generate() 会在该 worker 线程触发本函数，此后同线程复用，
    天然规避 JPype 跨线程 attach 的问题。
    """
    global _JVM_UP, _Generator
    if _JVM_UP:
        return
    with _JVM_LOCK:
        if _JVM_UP:
            return
        jar = _resolve_jar()
        if not jar.exists():
            raise FileNotFoundError(
                f"unidbg fat jar 不存在: {jar}\n"
                f"  1) 先在 Java 层字节级验证跑通（SKILL Phase 6.1）\n"
                f"  2) maven-shade 打全依赖: mvn package -DskipTests\n"
                f"  3) 或用 UNIDBG_JAR 指向产物路径"
            )
        import jpype
        import jpype.imports  # noqa: F401  (启用 Java 包 → Python 模块映射)

        jvm_path = _resolve_jvm_path()
        if jvm_path:
            jpype.startJVM(jvm_path, classpath=[str(jar)])
        else:
            jpype.startJVM(jpype.getDefaultJVMPath(), classpath=[str(jar)])
        # startJVM 后才能解析 Java 类
        _Generator = jpype.JClass(_GENERATOR_CLASS)
        _JVM_UP = True


def generate(input: str) -> dict:
    """进程内直调 Java 补环境类，返回 SO 生成的参数。

    input 的语义由 Java 侧补环境类的 generate(String) 决定；按实际 SO 改。
    """
    _ensure_jvm()
    result = getattr(_Generator, _GENERATOR_METHOD)(input)
    return {"output": str(result)}
