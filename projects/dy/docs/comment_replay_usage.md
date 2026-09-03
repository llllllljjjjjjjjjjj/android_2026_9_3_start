# 评论接口 oracle 重放 + 翻页采集 — 使用说明

> 2026-08-27 定稿。脚本：`scripts/comment_replay.py`

## 用法

```bash
# 前置：真机抖音运行中（frida oracle 自动 attach）
python comment_replay.py                  # 模板翻页采集（count=50，最多 20 页）
python comment_replay.py --pages 30       # 翻 30 页
python comment_replay.py --from-charles   # 从 Charles 抓最新 list 请求做模板（换视频时用）
python comment_replay.py --aweme-id <id>  # 换视频（免 Charles）：只换 aweme_id，cursor=0 起翻页
python comment_replay.py --single         # 只重放一次（调试）
python comment_replay.py --cold <aweme_id>  # 实验：stream 首屏冷启动（见"已知限制"）



```

输出：`capture/comments_out.json`（去重后的评论对象数组，含 text/user/digg_count/cid 等全字段）。

## 换视频：两种方法

### 方法一：--from-charles（稳妥，已有模板会话基础）

1. 手机抖音打开目标视频评论区，翻一页（产生一条 `/aweme/v2/comment/list/` 请求）
2. `python comment_replay.py --from-charles --pages 30`（抓最新请求做模板并翻页）
3. 结果在 `capture/comments_out.json`

### 方法二：--aweme-id（免 Charles，实验 A 实证）

```
python comment_replay.py --aweme-id 7677083701695939786 --pages 30
```

原理（2026-08-27 实验 A）：list query 的 7 个"视频专属参数"（aweme_author /
authentication_token / top_query_word / common_flags / current_l1_comment_count /
comment_count / is_fold_list）**全部可砍**——oracle 照签八神、服务器 status=0 照回评论。
因此换视频 = 任意模板 + 只改 `aweme_id` + cursor 归零。第 1 页会打印
`[归属] 首条 aweme_id=... 匹配=...` 供确认返回的是目标视频的评论（此归属验证需
以本机实跑为准，实验 A 只验证了 status=0 + 返回 20 条）。

> 备注：body 仍是旧模板视频的 session 快照（ccd/cids），实验 A 显示服务器对此不拒绝。

## 翻页机制（实证结论）

| 项 | 结论 |
|----|------|
| 端点 | 首屏 `POST /aweme/v2/comment/list/stream/`（cursor=0）；翻页 `POST /aweme/v2/comment/list/` |
| body | **必须原样**。服务器把 `session_show_cids` 与客户端会话状态绑定校验，任何 cid 修改（真假都试过）→ -99999；zstd 重压缩（同语义）无碍 |
| query | 只改 `cursor`（= 上页响应 cursor）+ oracle 重新签名，其余参数照抄模板 |
| count | 上限 ~50（服务器 cap 48-50 条） |
| 重复带 | 某页 0 新条 → cursor 额外 +80 跳过（脚本自动） |
| 去重 | 客户端按 `cid` 去重（服务器不因 body 未更新而保证不重复） |
| 签名 | 八神头由 libmetasec_ml.so+0x28065c oracle 生成（`hooks/dy_hook21.js` RPC）；28065c 输入仅 URL+headers（含 x-ss-stub），不含 body |

实测：10 页 → 423 条去重评论（评论数 6 万+ 的视频）。

## 已知限制

1. **冷启动 -99999 待解（换视频已由 --aweme-id 绕过）**：stream 首屏 → 构造 list 第一页仍 -99999。
   实验 A 已证 7 个视频专属参数可全砍（minimal query 照签照回，换视频 = 只改 aweme_id），
   嫌疑转向 stream 响应与 list body 的 session 绑定（ccd/session_id 构造）。当前工作流：
   模板翻页直接用 --aweme-id，无需先在 app 里翻一页。
2. **IPv4 强制**：PC DNS 解析 api5-core-lf.amemv.com 到 IPv6（2409:...）时直连挂起，脚本已强制 IPv4。
3. **ttzip**：请求不声明 `ttzip-version` 且 accept-encoding 用 gzip, deflate, br（脚本自动），否则响应是 ttzip 需手动解。
4. **时间窗口**：模板捕获后 ~30 分钟内重放成功率最高（oracle 重签新 khronos 可放宽，但 body 快照越旧越易受评论区状态变化影响）。
