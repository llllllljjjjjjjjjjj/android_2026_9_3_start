# benchmark — risk-control-adversary（iteration 1）

| 用例 | with_skill | old_skill | delta |
|---|---|---|---|
| comment-chain-fullflow | 1.0 (6/6) | 0.5 (3/6) | +0.5 |
| risk-points-scan | 1.0 (6/6) | 0.833 (5/6) | +0.167 |
| search-chain-fullflow | 1.0 (8/8) | 0.5 (4/8) | +0.5 |

**均值**：with_skill 1.0 vs old_skill 0.611 （delta +0.389）

## 逐断言差异

### comment-chain-fullflow

| 断言 | with_skill | old_skill |
|---|---|---|
| B1 七层链路结构 | ✓ | ✗ |
| B2 前置依赖识别 | ✓ | ✓ |
| B3 三列联动配对表 | ✓ | ✓ |
| B4 因果分级(已实证/推测) | ✓ | ✗ |
| B5 降级分级判据 | ✓ | ✗ |
| B6 不确定结论标注 | ✓ | ✓ |

### risk-points-scan

| 断言 | with_skill | old_skill |
|---|---|---|
| C1 正确选工作流 D | ✓ | ✓ |
| C2 前置埋点专章 | ✓ | ✓ |
| C3 知识库沉淀清单 | ✓ | ✓ |
| C4 埋点实证发现 | ✓ | ✗ |
| C5 配对关系表 | ✓ | ✓ |
| C6 因果/待验证清单 | ✓ | ✓ |

### search-chain-fullflow

| 断言 | with_skill | old_skill |
|---|---|---|
| A1 七层链路结构 | ✓ | ✗ |
| A2 前置接口表 | ✓ | ✓ |
| A3 紧邻特征上报表 | ✓ | ✓ |
| A4 配对强度标注 | ✓ | ✗ |
| A5 因果验证表 | ✓ | ✓ |
| A6 降级分级判据 | ✓ | ✗ |
| A7 缺证据标注 | ✓ | ✓ |
| A8 时序≠因果纪律 | ✓ | ✗ |
