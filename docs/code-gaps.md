# 代码层缺口清单

## 总体判断
当前项目的核心规则引擎、sample/csv 端到端流程、scanner 语义层已经比较成熟。
代码层的主要缺口，不再是“规则不存在”，而是以下几类工程与数据事实层增强。

---

## P0：真实市值快照替代 provider / fallback
### 问题
当前已验证：
- `stock_basic` 可用
- `trade_cal` 不可用
- `daily_basic` 不可用

因此当前 Tushare token 只能承担股票列表刷新，不能承担真实市值快照刷新。

### 需要补的代码
- `src/market_cap/providers.py`
  - 增加替代 provider
  - 增加 fallback 逻辑
- `scripts/refresh_market_cap_snapshot.py`
  - 支持更清晰的 provider 选择 / fallback / cache

### 目标
让 scanner 的市值快照层拥有可持续的真实数据来源，而不是只依赖当前受限 token。

---

## P1：technical snapshot 输入/计算契约强化
### 当前已有
- `scripts/refresh_technical_snapshot_from_ohlcv.py`
- `src/technical/calculators.py`
- `src/technical/ohlcv_provider.py`

### 仍值得补的代码
- 更严格的 OHLCV 输入校验
- 更清晰的 metadata / 计算窗口输出
- 对复权口径、trade_date 顺序、重复行、缺失列的处理
- 为后续指标扩展保留稳定接口

### 目标
让 technical snapshot 的真实生成路径更稳、更适合作为长期主输入层。

---

## 已补：scanner 排序层
### 当前状态
当前 scanner 已新增：
- `src/scanner/ranking.py`
- `tests/test_ranking.py`
- `daily_scan_summary_cn.json` 中的 `ranking_model`

### 当前已支持
- `candidate/watch/reject` 分层排序
- major risk / reset 优先降级
- breakout / crossover / pullback 机会的显式优先级
- freshness、risk_flags、流通市值、总市值参与排序

### 备注
排序逻辑当前已经从 `scanner engine` 中拆出，便于继续独立演进和测试。

---

## 已补：formatter / 输出层
### 当前状态
当前已新增：
- `src/scanner/formatter.py`
- CLI 文本 review 输出
- `--text-summary-output`
- `--text-summary-limit-per-decision`

### 当前已支持
- 按 `candidate/watch/reject` 分组展示排序结果
- 每个 bucket 聚合 `Top reasons / Top signals / Top risks`
- Top N / 全量 ranked rows 两种查看模式

### 目标
在保留 CSV/JSON 的同时，补一层更适合人工日常复核的轻量文本摘要。

---

## 已补：配置层整理
### 当前状态
本轮已新增：
- `src/scanner/config.py`
- scanner summary threshold 导出统一走 `RuleBasedScanConfig.summary_thresholds()`
- `run_daily_scan.py` / `run_rule_based_flow.py` 共用同一套 scanner CLI 参数装配函数

### 当前已支持
- market cap / circulating market cap / breakout volume / no-chase / pullback freshness / support tolerance 阈值集中定义
- 派生 watch floor 统一由 config 计算
- formatter / summary / CLI stage print 复用同一份 threshold 语义

### 备注
参数默认值、摘要输出和 CLI wiring 不再散落在多处脚本里。

---

## 已补（本轮最小拆分）：scanner engine 模块化
### 当前状态
本轮已新增：
- `src/scanner/rules.py`
- `src/scanner/reason_builder.py`
- `src/scanner/record_builder.py`

### 当前已支持
- engine 只负责 lookup / orchestration
- 规则状态计算、reason/signal/risk 组装、record 构建都已有独立模块和测试覆盖

### 后续仍可选
- 如果规则继续明显扩张，再进一步拆成 `trend_rules.py` / `trigger_rules.py` / `risk_rules.py`

### 目标
先把 engine 从膨胀状态里拉出来，后续继续加规则时不必再把所有逻辑堆回一个文件。

---

## P2：测试体系继续增强
### 当前已有
- scanner tests
- flow CLI tests
- technical ohlcv pipeline tests

### 未来可补
- integration fixture 分层
- golden output tests
- ranking regression fixtures
- provider fallback tests

### 目标
让后续继续加规则、换 provider 时不容易回归。

---

## P2：仓库治理
### 当前问题
运行产物、数据目录和 memory 文件目前可能混入仓库。

### 需要补的代码/配置
- `.gitignore`
- 数据版本化策略说明
- 哪些文件是运行产物，哪些是应版本化的 seed/fixture

### 目标
让仓库后续维护更干净。

---

## 一句话总结
当前代码层后续最值得优先补的，不是继续大幅扩规则，而是：
1. 真实市值快照替代 provider / fallback
2. technical snapshot 输入契约强化
3. provider fallback / 仓库治理
4. 继续增强测试体系与跨日复核能力
