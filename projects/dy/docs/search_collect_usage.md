# 抖音搜索采集器使用说明（内存扫描 aweme_info 方案）

> 配套脚本：`scripts/search_collect.py`。
> 核心：搜索响应的 `aweme_info`（视频 id/标题/作者/统计）在 libsscronet **native 层**
> 用 C++ JSON（nlohmann/json）解析，Java 的 org.json/gson hook 抓不到。
> 本采集器用 **内存扫描**（Memory.scanSync 搜 "aweme_info" 字符串）直取完整字段。

## 一、原理

```
deep link 触发搜索（snssdk1128://search?keyword=美食）
  → App 发请求 + 收响应 + native 解析 → aweme_info 落内存
  → frida Memory.scanSync 扫内存找 "aweme_info" → 回溯 JSON 开头 → 正则提取字段
  → 输出 aweme_id / desc(标题) / author.nickname / digg_count(赞) / comment_count(评)
```

## 二、环境依赖

1. 真机 App 运行 + florida-server + `adb forward tcp:27042`
2. PC frida 客户端 `.venv-frida-16.5.7`（16.5.x）
3. 无需 Charles / 无需字典 / 无需签名（App 代发全自动）

## 三、用法

```powershell
& "D:\reserve_agent\ish-portable-kit\.venv-frida-16.5.7\Scripts\python.exe" `
  "D:\reserve_agent\ish-portable-kit\projects\dy\scripts\search_collect.py" `
  --kws "美食,火锅" --limit 10
```

参数：
| 参数 | 默认 | 说明 |
|------|------|------|
| `--kws` | `美食,火锅` | 逗号分隔搜索词 |
| `--limit` | 10 | 每词最多取几条 |

## 四、输出

`capture/search_collect_result.json`，每条字段：
```json
{
  "aweme_id": "7664911070490126501",
  "title": "乡村厨房🏠番茄虾仁滑蛋...",
  "author": "十一按时吃饭🥣",
  "author_uid": "103769027392835",
  "likes": "1163636",
  "comments": "17349",
  "collects": "",
  "keyword": "美食"
}
```

## 五、已知限制

1. **每次运行会 force-stop 重启 App**（清内存残留，冷启动 ~45s），保证结果干净。
2. **likes/comments 部分可能为空**：`statistics` 字段在 aweme_info 尾部，超出 12000 字符
   扫描窗口时取不到（长 desc + 多 url 列表会顶出窗口）。
3. **每词结果条数不固定**（首页 feed 预加载可能吃掉部分窗口），实测 3~10 条。
4. **残留兜底**：pre-scan 8s 扫掉启动期首页 feed，触发搜索后只取新增。

## 六、排障

| 现象 | 处理 |
|------|------|
| `pidof` 无输出 | 等 App 冷启动完成（脚本已内置 force-stop+monkey 拉起+45s） |
| 抓到 0 条 | 换全新关键词（缓存词不刷新）；或加大 `--limit` |
| 结果混入非搜索内容 | 增加 pre-scan sleep（`time.sleep(8)` 改大） |
