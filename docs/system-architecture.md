# 系统交互与底层逻辑说明

## 1. 系统定位
本项目是一个**规则驱动的 A 股决策支持扫描器**，不是自动交易系统，也不是由 LLM 单独拍板买卖的投顾系统。

当前目标：
- 准备股票池
- 准备市值快照与技术快照
- 运行透明、可解释的规则扫描
- 输出 `candidate / watch / reject`、分数和原因
- 由用户保留最终买卖决策权

## 2. 当前交互方式

### 2.1 命令行交互
当前主要通过 CLI 使用。

#### 分步执行
- `scripts/refresh_stock_list.py`
- `scripts/build_stock_index.py`
- `scripts/refresh_market_cap_snapshot.py`
- `scripts/refresh_technical_snapshot.py`
- `scripts/run_daily_scan.py`

#### 一键执行
- `scripts/run_rule_based_flow.py`

该一键脚本会顺序完成：
1. 股票列表刷新
2. universe 构建
3. 市值快照刷新
4. 技术快照刷新
5. 日扫描输出

### 2.2 未来聊天交互
未来可通过聊天入口触发同一套规则流，例如：
- 扫一下今天的 A 股机会
- 看看市值大于 100 亿的候选股
- 只返回 candidate

但聊天只是**触发入口**，实际决策仍由规则引擎完成，而不是由聊天模型直接决定买卖。

## 3. 底层分层逻辑

### 3.1 股票列表层
负责准备最基础的股票列表。

输入来源：
- sample
- csv
- 未来可扩展到 Tushare 等 provider

输出：
- `data/raw/stock_list_cn.csv`
- `data/raw/stock_list_cn.meta.json`

作用：定义后续可参与 universe 构建的股票列表。

### 3.2 Universe 构建层
负责从股票列表中构建**可参与扫描的股票池**。

当前基础过滤包括：
- 是否是 A 股
- 是否正常上市
- 是否 ST（默认排除）

输出：
- `data/derived/universe_cn.csv`
- `data/derived/stock_index_cn.json`
- `data/derived/universe_summary_cn.json`

作用：先完成“谁有资格进入后续扫描”的预筛选。

### 3.3 事实快照层
当前拆分为两类事实快照。

#### 市值快照层
记录：
- 总市值
- 流通市值
- 日期
- 股票代码/名称

输出：
- `data/raw/market_cap_snapshot_cn.csv`
- `data/raw/market_cap_snapshot_cn.meta.json`

#### 技术快照层
记录：
- 收盘价
- 前收盘价
- 日内低点
- SMA20
- SMA60
- 前一日 SMA20 / SMA60
- breakout 参考位
- `volume_ratio_20d`
- 日期
- 股票代码/名称

输出：
- `data/raw/technical_snapshot_cn.csv`
- `data/raw/technical_snapshot_cn.meta.json`

作用：把“原始事实”和“扫描规则”分开。后续更换数据源时，只要快照格式保持一致，扫描器逻辑无需重写。

### 3.4 规则扫描层
当前核心扫描器为：
- `RuleBasedScanner`

输入：
- universe records
- market-cap snapshot
- technical snapshot

当前评估的规则包括：

#### 市值规则
- `candidate_band`
- `watch_band`
- `below_watch_band`
- `missing`

#### 技术规则 1：close vs SMA20
- `pass`
- `fail`
- `missing`

#### 技术规则 2：SMA20 vs SMA60
- `pass`
- `fail`
- `missing`

#### 技术规则 3：SMA20 金叉确认
- `confirmed_bullish_cross`
- `touching_sma60`
- `crossed_but_close_not_above_prev_close`
- `missing_price_confirmation_context`
- `already_above`
- `fail`
- `missing`

#### 技术规则 4：breakout 确认
- `pass`
- `stale_above_breakout`
- `failed_breakout`
- `fail`
- `missing`

#### 技术规则 5：breakout 量能确认
- `pass`
- `fail`
- `not_applicable`
- `missing`

#### 技术规则 6：supported pullback 确认
- `confirmed_supported_pullback`
- `support_retested_without_pullback_day`
- `support_not_tested`
- `closed_below_sma20`
- `undercut_sma20_support`
- `missing`

#### 技术规则 7：pullback 量能确认
- `pass`
- `fail`
- `not_applicable`
- `missing`

#### 技术规则 8：pullback 新鲜度确认
- `pass`
- `rebounded_too_far_above_sma20`
- `not_applicable`
- `missing`

#### 技术规则 9：不追高保护
- `pass`
- `overextended`
- `not_applicable`
- `missing`

输出字段包括：
- `decision`
- `score`
- `max_score`
- `reason`
- `market_cap_rule`
- `circulating_market_cap_rule`
- `close_vs_sma20_rule`
- `sma20_vs_sma60_rule`
- `sma20_crossover_rule`
- `breakout_rule`
- `breakout_volume_rule`
- `pullback_support_rule`
- `pullback_volume_rule`
- `pullback_freshness_rule`
- `no_chase_rule`
- `signal_reasons`
- `risk_flags`

### 3.5 排序层
当前规则扫描之后，会进入一层独立排序：

- 实现位置：`src/scanner/ranking.py`
- 输入：`DailyScanRecord`
- 输出：同一批 record 的稳定排序结果

当前排序不会重写 `candidate/watch/reject` 决策，只负责决定“谁排在前面”。

当前排序维度按顺序包括：
- `decision`
- `major risk tier`
- `score`
- confirmed trigger 数量
- confirmed trigger 语义优先级
- trigger freshness / quality
- `risk_flags` 数量
- 流通市值 / 总市值
- `symbol`

这样做的目标是：
- 不让高分但已出现 reset / structural risk 的 `watch` 排得过前
- 让同分 `candidate/watch` 更适合人工复核

### 3.6 结果输出层
当前输出：
- `data/derived/daily_scan_cn.csv`
- `data/derived/daily_scan_summary_cn.json`
- 可选 `--text-summary-output` 文本复核摘要

输出内容包括：
- candidate/watch/reject 数量
- 每只股票的规则结果
- 分数
- 排序后的结果顺序
- `ranking_model`
- 原因
- summary 统计

当前人读输出路径也已经单独抽象为 formatter：
- 实现位置：`src/scanner/formatter.py`
- 输入：`DailyScanResult + RuleBasedScanConfig`
- 输出：按 `candidate/watch/reject` 分组的文本摘要
- 文本摘要显式复用已有 `decision`、`score`、`reason`、`signal_reasons`、`risk_flags` 和 ranking semantics，不新增第二套决策模型
- `scripts/run_daily_scan.py` 与 `scripts/run_rule_based_flow.py` 默认都会把这份 text review 打到 stdout，并可选落地为 `.txt`

## 4. 当前决策机制

### 4.1 谁在做分类决策
当前由**规则引擎**负责决定：
- `candidate`
- `watch`
- `reject`

规则依据是显式的、可解释的事实与阈值，而不是 LLM 的自由生成结论。

### 4.2 LLM 的角色
当前项目不依赖 LLM 做底层分类决策。

未来如果接入 LLM，也只建议用于：
- 解释规则结果
- 生成自然语言报告
- 总结风险点

LLM 不负责：
- 单独决定买卖
- 触发自动下单

### 4.3 最终拍板人
当前设计下：
- 规则引擎负责分类与评分
- 用户负责最终买入/卖出决策

这是项目明确固定的边界。

## 5. 当前扫描评分逻辑

当前阶段二规则评分为：
- `market_cap_candidate_band = 2`
- `market_cap_watch_band = 1`
- `circulating_market_cap_liquidity = 1`
- `close >= SMA20 = 1`
- `SMA20 >= SMA60 = 1`
- `confirmed_SMA20_cross = 1`
- `breakout_confirmation = 1`
- `breakout_volume_confirmation = 1`
- `supported_pullback_confirmation = 1`
- `pullback_volume_contraction = 1`
- `fresh_supported_pullback_entry = 1`
- `no_chase_guard = 1`

满分：`12`

这意味着：
- 市值达到 candidate band、趋势过滤通过、触发确认到位、且不过度偏离 `SMA20`，才进入 `candidate`
- fresh crossover 只有在 `SMA20` 当日真正收在 `SMA60` 上方、且 `close_price_cny > prev_close_price_cny` 时才成立；如果只是触到同一水平，会显式输出 `touching_sma60`，如果均线上穿已出现但收盘没有强于前收，则会显式输出 crossover 价格确认不足状态
- 如果依赖 breakout 作为触发，breakout 必须是 fresh breakout，且还必须有 `volume_ratio_20d` 的量能确认；stale / failed breakout 会被显式输出但不会当作触发
- 如果依赖 supported pullback 作为触发，必须显式看到 `SMA20` 支撑测试、回踩日收盘不高于前收，`volume_ratio_20d` 不高于回踩量能上限，且收盘没有反弹得离 `SMA20` 太远
- 如果同一天出现 `failed_breakout`，即使也看到 supported pullback，当前也只会保留在 `watch`，等待 breakout failure 影响先重置
- 市值过线但趋势、触发或不追高保护任一不足，进入 `watch`
- 市值低于 watch band 或缺少关键事实，进入 `reject`

## 6. 当前明确不做的事情
项目当前明确不做：
- 自动下单
- 自动卖出
- 通知系统
- 调度系统
- Web UI
- Bot 层
- 完整回测/风控/执行平台
- 让 LLM 单独拍板买卖

## 7. 当前能力边界

### 已具备
- token-free 的 sample/csv 端到端规则流
- 股票列表、universe、市场值快照、技术快照、规则扫描的完整链路
- 一键 CLI 与分步 CLI
- candidate/watch/reject + 分数 + 原因输出
- 测试覆盖 sample/csv 流

### 尚未完成
- 真实技术快照 provider / OHLCV 集成
- 从真实 OHLCV 自动推导技术快照
- 更复杂的技术规则（如量价确认、RSI/MACD、波动率过滤）
- 真实每日定时运行集成

## 8. 一句话总结
本项目当前是一个：

> **规则驱动、可解释、可测试的 A 股机会筛选引擎**

它负责提供决策支持，而不是替用户自动做买卖决策。
