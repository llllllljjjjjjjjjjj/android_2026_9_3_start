# risk-control-adversary — 测试记录（永久档案）

> 每次测试的结论都沉淀在这里，避免重复踩坑。原始数据在 `risk-control-adversary-workspace/` 下。

## 一、测试方法

- 3 个 eval：eval-0 方案生成（资料丰富的目标）、eval-1 学习风控指导文档、eval-2 方案生成（资料极薄目标，测诚实性）
- 每个 eval 跑 with_skill / without_skill 双对照（baseline 禁读 skill 与测试脚手架文件）
- 断言由独立评分员逐条核对（读 outputs + 参照输入资料，输出 grading.json：text/passed/evidence）
- 聚合脚本：`cd C:/Users/lenovo/.claude/skills/skill-creator && PYTHONUTF8=1 python -m scripts.aggregate_benchmark <iteration-dir> --skill-name risk-control-adversary`

## 二、测试历史

| 轮次 | 目标 | 结果 | 结论 |
|---|---|---|---|
| iteration-1 | projects/dy、dcgc（真实） | With 100%±0% vs Without 75%±25%，Delta +0.25 | baseline 通过探索 workspace 学到了格式约定（脚手架泄漏），区分度失真；dcgc baseline 有 38→19 DEX 数量等事实错误 |
| **iteration-3** | **虚构靶标 fictionmall / fictionnews** | **With 100%±0% vs Without 48%±13%，Delta +0.52** | **当前有效基线**，详见下节 |

## 三、iteration-3 详细结果（2026-08-27）

| Eval | 场景 | With | Without | 差距点 |
|---|---|---|---|---|
| eval-0 fictionmall | 方案生成（4 接口+签名+实测节奏资料） | 8/8 | 4/8 | baseline 自创 D1-D7 维度替代五维分类、缺请求策略与真人模拟板块、缺工具链映射、缺统一方案结构 |
| eval-1 学习文档 | 沉淀风控指导文档经验 | 6/6 | 2/6 | 格式泄漏修复后区分度恢复：baseline 提炼质量不差（17 条）但完全没落到 E- 格式/编号/索引 |
| eval-2 fictionnews | 方案生成（仅 README） | 5/5 | 3/5 | baseline 诚实（零虚构、事实引用全对）但缺接口总览结构与保守起步节奏建议 |

**聚合**：With 100%±0% vs Without 48%±13%，Delta +0.52；耗时 +4.4s（可忽略）；tokens +6,576/run（≈+18%，固定开销 6k 加载 + 知识库写入，不随项目变大）

**run 消耗明细**（tokens）：eval-0 38,479/33,917；eval-1 53,247/46,882；eval-2 35,479/26,679（with/without）。评分 6 run 合计 256,555。整轮 ≈49.1 万。

## 四、关键结论

**skill 的增量在三处**（baseline 系统性缺失，这是 skill 的价值所在）：
1. 请求策略与真人模拟板块（逆向期/数据期分期、节奏对拍、行为序列、参数完整性）
2. 五维分类 + 证据等级统一框架
3. 知识库 E- 格式/编号/索引落地

**baseline 不弱的方面**：诚实性（虚构目标如实说明、未知不编造）是模型基础能力，不是 skill 带来的——诚实性断言未来降权，不应作为 skill 的卖点。

**测试工程踩坑记录**（评分员/聚合脚本相关，写进下一次测试的注意事项）：
- 脚手架泄漏：baseline 若可读 eval_metadata.json 会学会格式 → baseline prompt 必须禁读脚手架文件
- grading.json 的 `summary.pass_rate` 必须写 0-1 小数（写百分数会导致聚合结果 ×100 错乱：3400%/1147%）
- grading.json 的 `timing.*` 必须写 0.0，否则聚合脚本跳过 timing.json 用 0 值
- eval_metadata.json 需复制进每个 `<config>/run-0/` 目录聚合才认
- 转录 .output 文件会被临时目录清理，token 分步统计要趁早做

## 五、评分员反馈的 eval 改进建议（下一轮迭代用）

1. eval-0 断言 5 中 frida-orchestrator-mcp 不在 skill 协作边界内 → 措辞改为「protocol-signature-reverser / android-dynamic / android-recon」
2. 断言 2 应明确「维度合并行」（一接口多维度放一行）是否允许
3. 建议新增环境完整性断言：运行未写入 skill 的 references/ 真实知识库
4. 断言 8（Web 情报如实说明）可要求检查 WebSearch 工具调用记录而非只看文案
5. 断言存在「区分度」维度差异：诚实性类断言 both 都能过，结构与策略类断言才拉开差距——迭代时优先加结构与策略断言

## 六、已知边界

- 对具名第三方平台的生产环境风控对抗无实测基线（历史测试在具名真实目标上无法完成），评估与验证建议用自有/可复现目标进行。
