# Implementation Status

## 已实现

当前仓库已经具备一版可用基础设施，范围严格控制在“股票列表刷新 + universe 构建 + 事实快照刷新 + 轻量规则扫描输出”：

- `scripts/refresh_stock_list.py`
  - 支持 `sample`、`csv`、`tushare` 三种 provider 入口
  - 默认可用的是 `sample`，无需任何外部依赖即可跑通
  - `tushare` 路径当前优先尝试官方 `tushare` SDK，并按用户提供的参考写法设置 `pro._DataApi__http_url = 'http://118.89.66.41:8010/'`
  - 如果本地没有安装 `tushare` 包，则自动回退到仓库内置 HTTP 请求，直接调用 `stock_basic`
  - 使用 `tushare` 时仍然需要可用 token、该 token 具备 `stock_basic` 权限（Tushare 官方文档当前写明为 `2000` 积分起），以及对目标地址的网络连通性
  - 产出标准化 A 股股票列表 CSV 和 metadata JSON
- `scripts/build_stock_index.py`
  - 从标准化股票列表构建第一版 A 股 universe
  - 默认过滤 ST、退市/非上市状态、非 A 股代码
  - 输出 universe CSV、股票索引 JSON、构建摘要 JSON
- `scripts/refresh_market_cap_snapshot.py`
  - 支持 `sample`、`csv`、`tushare` 三种 provider 入口
  - 默认可用的是 `sample`
  - `tushare` 路径当前使用 `daily_basic` 作为市值快照主接口，最小字段集为 `ts_code,trade_date,total_mv,circ_mv`
  - 如果未显式指定 `--trade-date`，会先调用 `trade_cal` 自动选择最近实际可刷新的开市日
  - `daily_basic` 的 `total_mv/circ_mv` 文档单位为“万元”，写入仓库前会统一转换为 `billion_cny`
  - 当前 `symbol` 由 `ts_code` 派生，`name` 留空；这是刻意保持最小真实数据接入，不额外引入第二层名称补齐逻辑
  - 使用 `tushare` 时仍然需要可用 token、该 token 具备 `daily_basic` 与 `trade_cal` 权限（Tushare 官方文档当前均写明为 `2000` 积分门槛），以及对目标地址的网络连通性
  - 产出标准化市值快照 CSV 和 metadata JSON
  - 当前统一单位为 `billion_cny`
- `scripts/refresh_technical_snapshot.py`
  - 支持 `sample`、`csv` 两种 provider 入口
  - 默认可用的是 `sample`
  - 产出标准化技术快照 CSV 和 metadata JSON
  - 当前承载 scanner 已明确使用的阶段二字段：
    - `close_price_cny`
    - `prev_close_price_cny`
    - `low_price_cny`
    - `sma20_cny`
    - `sma60_cny`
    - `prev_sma20_cny`
    - `prev_sma60_cny`
    - `breakout_level_cny`
    - `volume_ratio_20d`
- `scripts/refresh_technical_snapshot_from_ohlcv.py`
  - 新增本地 OHLCV CSV -> technical snapshot 的最小真实链路
  - 当前支持从本地 `ts_code/trade_date/high/low/close/(volume)` 历史自动推导 scanner 已依赖的技术字段
  - `breakout_level_cny` 当前定义为“不含最新日的前 20 个交易日最高价”
  - `volume_ratio_20d` 当前定义为“最新成交量 / 前 20 个交易日平均成交量”；如果输入没有 volume，则该字段留空
  - 产出标准化技术快照 CSV 和 metadata JSON
- `scripts/run_daily_scan.py`
  - 读取已构建的 universe CSV、市值快照 CSV、技术快照 CSV
  - 当前明确实现一组计分/过滤规则，且 crossover / breakout 结果都进一步细化为显式状态：
    - `total_market_cap_billion_cny` 是否进入 `candidate_band`
    - `close_price_cny >= sma20_cny`
    - `sma20_cny >= sma60_cny`
    - `prev_sma20_cny <= prev_sma60_cny && sma20_cny > sma60_cny`；如果今日 `sma20_cny == sma60_cny`，会显式记为 `touching_sma60`，而不是 fresh crossover；如果均线上穿已出现但收盘没有高于前收，则显式记为 `crossed_but_close_not_above_prev_close`；如果缺少 `prev_close_price_cny`，则显式记为 `missing_price_confirmation_context`
    - `prev_close_price_cny < breakout_level_cny <= close_price_cny`；昨收已在 `breakout_level_cny` 上方时显式记为 `stale_above_breakout`，昨收在上方但今收回下方时显式记为 `failed_breakout`
    - 当 breakout 被用作触发时，`volume_ratio_20d >= min_breakout_volume_ratio`
    - `low_price_cny` 是否在 `SMA20` 容忍带内测试支撑、且 `close_price_cny >= sma20_cny`
    - 当 supported pullback 被用作触发时，`close_price_cny <= prev_close_price_cny` 且 `volume_ratio_20d <= max_pullback_volume_ratio`
    - `close_price_cny <= sma20_cny * (1 + max_close_above_sma20_ratio)`
  - 输出 `candidate / watch / reject` 三类结果
  - 输出透明分数、逐条规则状态、`signal_reasons` 和 `risk_flags`，便于样例 / CSV 工作流人工复核
  - 当前扫描结果会再经过独立排序层：先看 `decision`，再看 `major risk tier`、`score`、confirmed trigger mix、trigger freshness/quality、`risk_flags` 数量与流动性代理
  - `daily_scan_summary_cn.json` 当前也会输出 `ranking_model`，把排序维度显式暴露出来
  - 当前 stdout 已切到 text review formatter：按 `candidate/watch/reject` 分组展示排序结果，并把 `reason`、`signal_reasons`、`risk_flags` 与 ranking tier 一起压缩成可快速人工复核的摘要
  - text review 当前会按 bucket 聚合 `Top reasons / Top signals / Top risks`，帮助先看主要正向确认和阻塞点
  - 支持 `--text-summary-limit-per-decision` 控制每个 bucket 展示多少条排序结果，支持 `0` 表示展示全部
  - 支持 `--text-summary-output` 额外把这份人工复核摘要落地为纯文本文件，同时保留原有 CSV/JSON 输出
  - 仅做决策支持输出，不产生任何交易执行动作
- `scripts/run_rule_based_flow.py`
  - 新增一键端到端 CLI，顺序执行：
    - 股票列表刷新
    - universe 构建
    - 市值快照刷新
    - 技术快照刷新
    - 日扫描输出
  - 当前一键流刻意只支持 `sample` / `csv` 输入，避免把 token/provider 复杂度引入默认工作流
  - 支持 `--data-root`，可把整套 `raw/derived` 输出写到独立目录，方便样例验证和 CSV 集成测试
- `src/data_provider/`
  - 定义 `StockListProvider` 抽象接口
  - 定义 `StockListRecord` 数据结构
  - 提供 CSV 读写工具
  - 提供 `SampleStockListProvider`、`CSVStockListProvider`、`TushareStockListProvider`
- `src/market_cap/`
  - 定义 `MarketCapSnapshotProvider` 抽象接口
  - 定义 `MarketCapSnapshotRecord` 数据结构
  - 提供市值快照 CSV 读写工具
  - 提供 `SampleMarketCapSnapshotProvider`、`CSVMarketCapSnapshotProvider`
  - 为未来真实 provider 保留清晰扩展点
- `src/scanner/`
  - 定义 `RuleBasedScanConfig`、`DailyScanRecord`、`DailyScanResult`
  - 新增 `src/scanner/config.py`，统一收敛 scanner 阈值默认值、summary threshold 导出，以及 CLI 参数装配
  - 提供 `RuleBasedScanner`
  - 新增 `src/scanner/rules.py`、`src/scanner/reason_builder.py`、`src/scanner/record_builder.py`，把规则状态计算、reason/signal/risk 组装、record 构建从 engine 中拆出
  - 新增 `src/scanner/ranking.py`，把排序逻辑从 scanner engine 中拆出
  - 新增 `src/scanner/formatter.py`，把“面向人工的 review 输出”从 CLI 中拆出，保持轻量、显式、可单元测试
  - 当前评分模型固定且透明：
    - `candidate_band` = `2`
    - `watch_band` = `1`
    - `circulating_market_cap_liquidity` = `1`
    - `close >= sma20` = `1`
    - `sma20 >= sma60` = `1`
    - `confirmed_sma20_cross` = `1`
    - `breakout_confirmation` = `1`
    - `breakout_volume_confirmation` = `1`
    - `supported_pullback_confirmation` = `1`
    - `pullback_volume_contraction` = `1`
    - `fresh_supported_pullback_entry` = `1`
    - `no_chase_guard` = `1`
    - 满分 `12`
  - 当前 `candidate` 判定必须同时满足：
    - 市值进入 `candidate_band`
    - `close >= sma20`
    - `sma20 >= sma60`
    - 金叉确认成立（当前还要求 crossover 当日 `close_price_cny > prev_close_price_cny`），或 fresh breakout 确认同时通过量能确认，或 supported pullback 确认同时通过回踩量能约束
    - 若同日出现 `failed_breakout`，即使 supported pullback 也成立，当前仍保持 `watch`
    - 不触发“不追高”保护
  - 当前排序层显式遵循：
    - `candidate > watch > reject`
    - hard reset / structural risk 先降序列位，再比较 `score`
    - 同分时比较 confirmed trigger 数量与语义：`supported_pullback > volume_backed_breakout > confirmed_crossover`
    - 再比较 freshness / quality、`risk_flags` 数量和流动性代理
  - 把 universe、市场事实快照、技术事实快照显式分层
- `src/technical/`
  - 定义 `TechnicalSnapshotRecord` 数据结构
  - 提供技术快照 CSV 读写工具
  - 提供 `SampleTechnicalSnapshotProvider`、`CSVTechnicalSnapshotProvider`
  - 为未来真实行情 / 指标 provider 保留清晰扩展点
- `src/universe/`
  - 定义 universe 构建配置与结果模型
  - 提供 `AShareUniverseBuilder`
  - 提供 `StockIndexBuilder`
  - 提供 universe CSV 读写，供 scanner 复用

## 明确保留为 TODO

以下内容还没有进入第一版基础设施：

- 真实历史行情 / OHLCV 获取
- 更稳定的远程 technical provider / fallback / 缓存策略
- 让一键 flow 直接吃原始 OHLCV 而不是先生成 technical snapshot
- 更丰富的量价确认、RSI/MACD、波动率等技术规则
- 更完整的候选评分、风险提示、操作模板
- LLM 解释层
- 定时调度
- Skill 集成
- Web UI / Bot / 通知
- 自动交易、风控执行、下单隔离层

## 设计边界

当前实现只做“事实数据准备 + 轻量规则筛选”，不做交易建议自动执行：

- 输出是股票列表、基础 universe、搜索索引、市值快照、技术快照、扫描结果
- 不包含买卖指令
- 不包含自动下单逻辑
- 不包含通知、调度编排
- 不让 LLM 单独做交易决策

## 当前默认输出

- `data/raw/stock_list_cn.csv`
- `data/raw/stock_list_cn.meta.json`
- `data/raw/market_cap_snapshot_cn.csv`
- `data/raw/market_cap_snapshot_cn.meta.json`
- `data/raw/technical_snapshot_cn.csv`
- `data/raw/technical_snapshot_cn.meta.json`
- `data/derived/universe_cn.csv`
- `data/derived/stock_index_cn.json`
- `data/derived/universe_summary_cn.json`
- `data/derived/daily_scan_cn.csv`
- `data/derived/daily_scan_summary_cn.json`

可选输出：

- 通过 `--text-summary-output` 生成的人工复核文本摘要，例如 `daily_scan_review.txt`

如果通过 `scripts/run_rule_based_flow.py --data-root /path/to/run-data` 运行，同样会在对应的 `/path/to/run-data/raw` 和 `/path/to/run-data/derived` 下生成同名文件。

## 已验证流程

本轮已实际验证以下流程可用：

- 分步示例流：
  - `python3 scripts/refresh_stock_list.py --provider sample`
  - `python3 scripts/build_stock_index.py`
  - `python3 scripts/refresh_market_cap_snapshot.py --provider sample`
  - `python3 scripts/refresh_technical_snapshot.py --provider sample`
  - `python3 scripts/run_daily_scan.py`
- 一键示例流：
  - `python3 scripts/run_rule_based_flow.py --data-root /tmp/a-share-scan-run`
- 一键 CSV 流（使用仓库内 seed 合约做验证）：
  - `python3 scripts/run_rule_based_flow.py --data-root /tmp/a-share-scan-csv --stock-list-provider csv --stock-list-input data/seeds/sample_stock_list_cn.csv --market-cap-provider csv --market-cap-input data/seeds/sample_market_cap_snapshot_cn.csv --technical-provider csv --technical-input data/seeds/sample_technical_snapshot_cn.csv`
- 自动化测试：
  - `python3 -m unittest discover -s tests -v`

## 下一步推荐

下一步最合适的是继续增强事实层和 scanner，而不是扩张外围系统：

- 补真实 OHLCV / 指标生成链路
- 在 scanner 层继续增加可复现规则
- 在现有 text review formatter 之上，继续细化 watch/reject 的阻塞原因聚合与跨日变化对比
- 继续明确保持“不通知、不调度、不自动下单”的边界
