# A-Share Opportunity Scanner

轻量化 A 股机会扫描项目。

系统定位遵循 [docs/decision-mechanism.md](/root/.openclaw/workspace/projects/a-share-opportunity-scanner/docs/decision-mechanism.md)：这是一个决策支持扫描器，不是自动交易系统。

## 当前已实现

- A 股股票列表刷新基础流程
- 本地 CSV / 示例数据 / 可选 Tushare 的统一 provider 接口
- A 股基础 universe 构建
- 静态股票索引导出
- 市值快照刷新流程
- 技术快照刷新流程（示例 / CSV）
- 本地 OHLCV CSV -> technical snapshot 生成链路
- 日扫描入口：`candidate / watch / reject` + 透明分数输出 + 显式排序层
- 面向人工复核的 text formatter：默认 stdout 展示分组排序摘要，可选落地为 `.txt`
- 一键端到端 CLI：可直接从 `sample` / `csv` 输入跑完整规则流
- 明确的已实现 / TODO 文档

当前排序策略见 [docs/ranking-policy.md](/root/.openclaw/workspace/projects/a-share-opportunity-scanner/docs/ranking-policy.md)。

## 快速开始

使用内置示例数据一键跑通当前最小规则流：

```bash
python3 scripts/run_rule_based_flow.py
```

如果要把结果写到独立目录，避免覆盖仓库默认样例输出：

```bash
python3 scripts/run_rule_based_flow.py --data-root /tmp/a-share-scan-run
```

如果你已经有自己的标准化 CSV，也可以一键跑完整流程：

```bash
python3 scripts/run_rule_based_flow.py \
  --data-root /tmp/a-share-scan-csv \
  --stock-list-provider csv --stock-list-input /path/to/stock_list.csv \
  --market-cap-provider csv --market-cap-input /path/to/market_cap_snapshot.csv \
  --technical-provider csv --technical-input /path/to/technical_snapshot.csv
```

仍然保留分步 CLI，便于单独刷新某一层数据：

```bash
python3 scripts/refresh_stock_list.py --provider sample
python3 scripts/build_stock_index.py
python3 scripts/refresh_market_cap_snapshot.py --provider sample
python3 scripts/refresh_technical_snapshot.py --provider sample
python3 scripts/refresh_technical_snapshot_from_ohlcv.py --input /path/to/ohlcv.csv
python3 scripts/run_daily_scan.py
```

`run_daily_scan.py` 和 `run_rule_based_flow.py` 现在默认都会在 stdout 打印一版按 `candidate/watch/reject` 分组、按当前 ranking semantics 排序后的人工复核摘要。每个 bucket 会先聚合 `Top reasons / Top signals / Top risks`，默认展示前 `5` 条排序结果；如果要看全部排序结果：

```bash
python3 scripts/run_daily_scan.py --text-summary-limit-per-decision 0
```

如果希望把同样的人工复核摘要落地成文本文件：

```bash
python3 scripts/run_daily_scan.py \
  --text-summary-output /tmp/daily_scan_review.txt

python3 scripts/run_rule_based_flow.py \
  --data-root /tmp/a-share-scan-run \
  --text-summary-output /tmp/a-share-scan-run/daily_scan_review.txt
```

输出文件默认位于：

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

- 通过 `--text-summary-output` 额外生成人工复核文本摘要，例如 `daily_scan_review.txt`

如果要只运行分步版并接入你自己的 CSV：

```bash
python3 scripts/refresh_stock_list.py --provider csv --input /path/to/stock_list.csv
python3 scripts/build_stock_index.py
python3 scripts/refresh_market_cap_snapshot.py --provider csv --input /path/to/market_cap_snapshot.csv
python3 scripts/refresh_technical_snapshot.py --provider csv --input /path/to/technical_snapshot.csv
python3 scripts/run_daily_scan.py --min-total-market-cap-bn 150
```

如果你手里是本地 OHLCV 历史，而不是已经算好的 technical snapshot，也可以先生成标准技术快照，再复用现有 scanner：

```bash
python3 scripts/refresh_technical_snapshot_from_ohlcv.py \
  --input /path/to/ohlcv.csv \
  --output /tmp/technical_snapshot_cn.csv

python3 scripts/run_daily_scan.py \
  --technical-input /tmp/technical_snapshot_cn.csv
```

输入合约和计算语义见 [docs/technical-snapshot-from-ohlcv.md](docs/technical-snapshot-from-ohlcv.md)。

`refresh_stock_list.py` 和 `refresh_market_cap_snapshot.py` 现在都单独支持可选 Tushare provider，但当前“一键端到端”流刻意只覆盖 `sample/csv`，以保持无 token、可复现、可本地验证。

如果只想验证 Tushare 股票列表刷新，当前实现仍然保持“轻依赖优先”：

- 如果本地环境已经安装官方 `tushare` Python 包，provider 会优先走官方 SDK，并按用户给出的参考写法设置 `pro._DataApi__http_url = 'http://118.89.66.41:8010/'`
- 如果本地没有安装 `tushare`，则自动回退到仓库内置的 HTTP POST 路径，直接请求 Tushare Pro 的 `stock_basic` 接口

无论走哪条路径，最小前置条件仍然有三项：

- 提供 token：`export TUSHARE_TOKEN=...`，或直接传 `--tushare-token`
- 该 token 具备 `stock_basic` 接口权限；Tushare 官方文档当前写明此接口为 `2000` 积分起，`100` 积分账号不应预期可用
- 当前运行环境能访问对应的目标地址：
  - SDK 路径使用 `http://118.89.66.41:8010/`
  - 回退 HTTP 路径使用 `http://api.tushare.pro`

示例：

```bash
python3 scripts/refresh_stock_list.py --provider tushare --list-status L
```

如果要验证 Tushare 市值快照刷新，当前实现也保持同一条 token 路径：

- 提供 token 的方式不变：`TUSHARE_TOKEN` 或 `--tushare-token`
- 实际市值快照接口使用 `daily_basic`
- 当前最小字段选择为：
  - `ts_code`
  - `trade_date`
  - `total_mv`
  - `circ_mv`
- 归一化规则：
  - Tushare `total_mv` / `circ_mv` 文档单位为“万元”
  - 仓库输出统一转换为 `billion_cny`
  - `symbol` 由 `ts_code` 前缀派生
  - `name` 当前留空，因为 `daily_basic` 本身不返回股票名称
- 如果未显式传 `--trade-date`，provider 会先调用 `trade_cal` 自动选择一个“实际可刷新的最近开市日”：
  - 默认取最近开市日
  - 但如果当前是开市日且北京时间 `17:00` 之前，则回退到前一个开市日，避免盘中/盘后过早取当天 `daily_basic`
- Tushare 官方文档当前写明：
  - `daily_basic` 至少需要 `2000` 积分
  - `trade_cal` 需要 `2000` 积分

示例：

```bash
python3 scripts/refresh_market_cap_snapshot.py --provider tushare
python3 scripts/refresh_market_cap_snapshot.py --provider tushare --trade-date 20260326
```

当前仓库默认仍然不强依赖 `tushare` 包；只有在本地明确装了它时，才会启用上面的官方 SDK 路径。如果后续确实要给仓库加别的依赖，也不要往系统 Python 里直接 `pip install`；当前环境启用了 externally managed 限制，应该优先使用仓库本地虚拟环境处理。

当前市值快照 CSV 规范：

- `ts_code`
- `symbol`
- `name`
- `total_market_cap_billion_cny`
- `circulating_market_cap_billion_cny`
- `as_of_date`

当前技术快照 CSV 规范：

- `ts_code`
- `symbol`
- `name`
- `close_price_cny`
- `prev_close_price_cny`
- `low_price_cny`
- `sma20_cny`
- `sma60_cny`
- `prev_sma20_cny`
- `prev_sma60_cny`
- `breakout_level_cny`
- `volume_ratio_20d`
- `as_of_date`

本地 OHLCV 转换脚本当前支持：

- 必需列：`ts_code`、`trade_date`/`date`、`high`、`low`、`close`
- 可选列：`symbol`/`code`、`name`、`volume`/`vol`
- `breakout_level_cny` 当前定义为“不含最新日的前 20 个交易日最高价”
- `volume_ratio_20d` 当前定义为“最新成交量 / 前 20 个交易日平均成交量”；如果输入没有 volume，这个字段会留空

说明：

- `prev_close_price_cny` 用于把“fresh breakout / stale breakout / breakout failure”和“回踩整理”区分成显式事实，而不是在 scanner 里猜测日内语境
- `low_price_cny` 用于显式判断是否真的回踩 / 测试了 `SMA20` 支撑，给下一批 pullback 规则留出清晰合约
- `prev_sma20_cny` / `prev_sma60_cny` 用于显式判断 `SMA20` 是否刚刚上穿 `SMA60`
- `breakout_level_cny` 是外部准备好的突破参考位，当前通常可理解为近 20 日高点或平台压力位
- `volume_ratio_20d` 表示当日成交量相对近 20 日均量的倍数；当前用于约束 breakout 触发质量，也用于区分“缩量/平量回踩”与“放量回踩风险”
- 这六个扩展字段当前仍然是可选的；如果缺失，扫描器会把对应确认视为 `missing`，结果更偏向 `watch`

当前扫描器实际评估的规则：

- 市值带宽规则：`candidate_band = total_market_cap_billion_cny >= 阈值`
- 市值观察带：`watch_band = total_market_cap_billion_cny >= 阈值 * (1 - watch_buffer_ratio)`
- 流动性代理规则：`circulating_market_cap_billion_cny >= min_circulating_market_cap_billion_cny` 才能进入 `candidate`，默认阈值 `30 bn`，并共享同一套 `watch_buffer_ratio`
- 趋势规则 1：`close_price_cny >= sma20_cny`
- 趋势规则 2：`sma20_cny >= sma60_cny`
- 触发规则 1：fresh `SMA20/SMA60` 金叉要求 `prev_sma20_cny <= prev_sma60_cny && sma20_cny > sma60_cny`
- 金叉新鲜度语义：如果今日 `sma20_cny == sma60_cny`，则显式记为 `touching_sma60`，表示刚触及但尚未真正站上，不会被当作 fresh crossover trigger
- 金叉价格确认语义：当日均线真正上穿后，还要求 `close_price_cny > prev_close_price_cny` 才记为 `confirmed_bullish_cross`；如果收盘没有强于前收，会显式记为 `crossed_but_close_not_above_prev_close`；如果缺少 `prev_close_price_cny`，则显式记为 `missing_price_confirmation_context`
- 触发规则 2：fresh breakout，要求 `prev_close_price_cny < breakout_level_cny <= close_price_cny`
- breakout 新鲜度 / 失败语义：如果 `close_price_cny >= breakout_level_cny` 但 `prev_close_price_cny >= breakout_level_cny`，则显式记为 `stale_above_breakout`；如果昨日已在 breakout level 上方但今日收回下方，则显式记为 `failed_breakout`
- breakout 量能确认：当 breakout 被当作入场触发时，要求 `volume_ratio_20d >= min_breakout_volume_ratio`，默认下限 `1.2`
- 回踩支撑确认：`low_price_cny` 在 `SMA20` 容忍带内测试支撑，`close_price_cny >= sma20_cny`，且 `close_price_cny <= prev_close_price_cny`
- 回踩量能约束：当 supported pullback 被当作入场触发时，要求 `volume_ratio_20d <= max_pullback_volume_ratio`，默认上限 `1.0`
- 回踩触发新鲜度：当 supported pullback 被当作入场触发时，`close_price_cny` 还必须不高于 `sma20_cny * (1 + max_pullback_close_above_sma20_ratio)`，默认上限 `2%`
- 不追高保护：`close_price_cny <= sma20_cny * (1 + max_close_above_sma20_ratio)`，默认上限 `5%`
- 透明分数：
  - `candidate_band=2`
  - `watch_band=1`
  - `circulating_market_cap_liquidity=1`
  - `close>=sma20=1`
  - `sma20>=sma60=1`
  - `confirmed_sma20_cross=1`
  - `breakout_confirmation=1`
  - `breakout_volume_confirmation=1`
  - `supported_pullback_confirmation=1`
  - `pullback_volume_contraction=1`
  - `fresh_supported_pullback_entry=1`
  - `no_chase_guard=1`
  - 满分 `12`

当前分类逻辑：

- `candidate`：总市值进入 `candidate_band`、流通市值流动性代理通过、趋势双确认通过，且满足下列任一路径，同时不过度偏离 `SMA20`
  - `SMA20/SMA60` 金叉确认
  - fresh breakout 站上 `breakout_level`，并且 `volume_ratio_20d` 达到量能下限
  - `SMA20` 支撑回踩确认，`volume_ratio_20d` 没有高于回踩量能上限，且收盘仍然贴近 `SMA20`
  - 但如果同一天出现 `failed_breakout`，即使也满足 supported pullback 质量约束，当前仍只会停留在 `watch`，等待 breakout failure 影响先重置
- `watch`：市值至少进入 `watch_band`，但仍有任一候选条件未满足，例如：
  - 只在 `watch_band`
  - 总市值已过线，但 `circulating_market_cap_billion_cny` 只在流动性 watch band，或缺失该流动性上下文
  - 趋势过滤未通过
  - `SMA20` 只是刚好触到 `SMA60`，但还没有真正站上，当前金叉触发不够新鲜
  - `SMA20` 虽然当日上穿了 `SMA60`，但收盘没有高于前收，当前金叉缺少价格确认
  - `SMA20` 虽然当日上穿了 `SMA60`，但缺少 `prev_close_price_cny`，当前金叉价格确认上下文不完整
  - 缺少金叉 / breakout / supported pullback 触发确认
  - fresh breakout 已出现，但缺少量能确认或量能不足
  - 价格虽然仍在 `breakout_level` 上方，但该 breakout 已不是当日新触发
  - 刚突破后又收回 `breakout_level` 下方，触发 breakout failure 降级
  - failed breakout 当天虽然又回到 `SMA20` 附近获得支撑，也只会显式记为 recovery watch，而不会直接升回 `candidate`
  - 回踩支撑已出现，但缺少量能收敛上下文，或回踩伴随放量压力
  - 回踩虽然测试了 `SMA20`，但收盘反弹得离 `SMA20` 太远，当前 pullback trigger 已不够新鲜
  - 回踩过程中跌破 / 明显下刺 `SMA20`，触发风险降级
  - 触发满足但触发后已经过度偏离 `SMA20`，触发“不追高”降级
- `reject`：缺少市值快照，或总市值 / 流通市值流动性代理低于各自的 `watch_band`

当前扫描输出除了主 `reason` 之外，还会附带两组显式解释字段：

- `signal_reasons`：已经成立的正向确认码 / 构造性恢复码，例如 `fresh_breakout_level_cleared`、`failed_breakout_recovered_at_sma20_support`
- `risk_flags`：导致降级、等待或拒绝的风险 / 缺口码，例如 `pullback_volume_above_threshold`

说明：

- 当前 scanner 读取的仍然是“已经算好的技术快照 CSV”；本轮新增的是一个本地 OHLCV -> technical snapshot 预处理脚本，而不是让 scanner 在运行时自己抓取 / 回算历史行情
- 技术快照允许部分字段留空；缺失字段会显式体现为 `missing` 规则状态
- 旧版最小技术快照（只有 `close/sma20/sma60`）仍然兼容，但在当前阶段规则下通常只能进入 `watch`，直到补齐触发确认所需的上下文
- `circulating_market_cap_billion_cny` 当前被当作低成本流动性代理，而不是成交额/换手率的完整替代
- `volume_ratio_20d` 当前只服务于 breakout / pullback 质量确认，不会把项目扩展成自动量化执行系统
- 统一归一化后再扫描：市值用 `billion_cny`，技术数值用 `cny`
- 后续如接入 Tushare / Akshare / 其他 provider，只需先适配到这两份标准 CSV 合约
- 这仍然只是决策支持输出，不是自动交易系统

## 目录结构

- `scripts/refresh_stock_list.py`
- `scripts/build_stock_index.py`
- `scripts/refresh_market_cap_snapshot.py`
- `scripts/refresh_technical_snapshot.py`
- `scripts/refresh_technical_snapshot_from_ohlcv.py`
- `scripts/run_daily_scan.py`
- `scripts/run_rule_based_flow.py`
- `src/data_provider/`
- `src/market_cap/`
- `src/scanner/`
- `src/technical/`
- `src/universe/`
- `data/seeds/sample_stock_list_cn.csv`
- `data/seeds/sample_market_cap_snapshot_cn.csv`
- `data/seeds/sample_technical_snapshot_cn.csv`
- `docs/implementation-status.md`
- `docs/technical-snapshot-from-ohlcv.md`

## 当前明确不做

- 自动下单或交易执行
- 通知、机器人、Web UI
- 复杂调度系统
- 定时任务 / 调度编排
- 重型回测、风控执行、组合管理框架

## 参考说明

实现借鉴了 `/root/.openclaw/workspace/daily_stock_analysis-main` 中的两个轻量思路：

- 股票列表刷新先落地为 CSV
- 股票索引单独生成静态 JSON
- 市值快照先标准化落地，再由 scanner 读取派生结果

但没有引入其 Web、Bot、通知、多代理或重型分析模块。
