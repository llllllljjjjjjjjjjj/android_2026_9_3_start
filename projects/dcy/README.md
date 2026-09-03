# dcy —— 单词鸭（com.wordln.app）逆向项目

> **目标**：拿到"返回每本词书的接口"（词书列表 / 分类树 / 详情 / 单词）。

## 成果速览

**核心接口（匿名可调、无签名、`_time` 非必需）：**

| 接口 | 作用 | 路径 |
|------|------|------|
| ⭐ 搜索词书 | **返回每本词书** | `GET /tomato-word/_20241001/wordbook/searchWordBooks?q=<关键词>` |
| 我的词书 | 我的词书列表 | `GET /tomato-word/_20241001/wordbook/myWordBooks` |
| 词书类型 | 19 个分类 | `GET /tomato-word/_20241001/wordbook/getWordBookType` |
| 词书分类树 | 分类→教材→年级→Unit词书 | `GET /tomato-word/xxl/getTypeTreeByParentId/v2?parentId=<id>` |
| 词书详情 | book+unitList+user | `GET /tomato-word/_20241001/wordbook/getWordBookDetail?id=<id>` |
| ⭐ 整书单词 | **整本词书所有单词**（word/mean/音标/发音/例句） | `GET /tomato-word/_20241001/wordbook/wordList?type=<词书id>&pageSize=10000` |
| 单元单词 | 单个单元单词 | `GET /tomato-word/xxl/getWordsByUnitId?unitId=<id>` |
| 学习统计 | killed/learning/total | `GET /tomato-word/xxl/getWordBookStatistics?typeId=<id>` |

Base：`https://zhcn.api.wordln.com`；完整文档见 `docs/wordbook_api.md`。

## 目录
```
apk/         ← 原始 APK（原文件在 ../apk/dcy.apk）
decompiled/  ← jadx 反编译产物（24023 文件）
apk_unpacked/← apktool 解包（Manifest/资源/Smali）
capture/     ← 抓包日志 + 截图 + Hermes bundle 字符串
hooks/       ← Frida 脚本（okhttp_dump.js / api_probe.js）
scripts/     ← 运行器 + 独立客户端（wordbook_client.py）
so_analysis/ ← libhermes.so 等
docs/        ← wordbook_api.md 接口文档
```

## 关键发现
- App：单词鸭，React Native + **Hermes 字节码**（bundle 头部魔改，字符串表部分明文）
- 网络栈：OkHttp 4.x（RN fetch 封装）
- 后端：`zhcn.api.wordln.com`，路径前缀 `/tomato-word/` 与 `/tomato-word/_20241001/`
- **词书接口匿名可访问、无签名、时间戳不校验** → 可直接脚本化调用
- 词书树：分类（学前/小学/初中/高中/大学）→ 教材（人教版PEP 等）→ 年级/册 → Unit（每 Unit = 一本词书）

## 复现步骤
1. Frida：`frida -H 127.0.0.1:27042 -f com.wordln.app -l hooks/okhttp_dump.js`（需 f1657/florida server）
2. 进"词库"tab → "更换词库" → 触发 `getTypeTreeByParentId` / `searchWordBooks`
3. 独立调用：`python scripts/wordbook_client.py search 小学`（需可直连外网的机器）
