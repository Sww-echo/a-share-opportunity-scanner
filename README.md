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
- 日扫描入口：`candidate / watch / reject` + 透明分数输出
- 一键端到端 CLI：可直接从 `sample` / `csv` 输入跑完整规则流
- 明确的已实现 / TODO 文档

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
python3 scripts/run_daily_scan.py
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

如果要只运行分步版并接入你自己的 CSV：

```bash
python3 scripts/refresh_stock_list.py --provider csv --input /path/to/stock_list.csv
python3 scripts/build_stock_index.py
python3 scripts/refresh_market_cap_snapshot.py --provider csv --input /path/to/market_cap_snapshot.csv
python3 scripts/refresh_technical_snapshot.py --provider csv --input /path/to/technical_snapshot.csv
python3 scripts/run_daily_scan.py --min-total-market-cap-bn 150
```

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

说明：

- `prev_close_price_cny` 用于把“上涨突破”和“回踩整理”区分成显式事实，而不是在 scanner 里猜测日内语境
- `low_price_cny` 用于显式判断是否真的回踩 / 测试了 `SMA20` 支撑，给下一批 pullback 规则留出清晰合约
- `prev_sma20_cny` / `prev_sma60_cny` 用于显式判断 `SMA20` 是否刚刚上穿 `SMA60`
- `breakout_level_cny` 是外部准备好的突破参考位，当前通常可理解为近 20 日高点或平台压力位
- `volume_ratio_20d` 表示当日成交量相对近 20 日均量的倍数；当前用于约束 breakout 触发质量，也用于区分“缩量/平量回踩”与“放量回踩风险”
- 这六个扩展字段当前仍然是可选的；如果缺失，扫描器会把对应确认视为 `missing`，结果更偏向 `watch`

当前扫描器实际评估的规则：

- 市值带宽规则：`candidate_band = total_market_cap_billion_cny >= 阈值`
- 市值观察带：`watch_band = total_market_cap_billion_cny >= 阈值 * (1 - watch_buffer_ratio)`
- 趋势规则 1：`close_price_cny >= sma20_cny`
- 趋势规则 2：`sma20_cny >= sma60_cny`
- 触发规则 1：`prev_sma20_cny <= prev_sma60_cny && sma20_cny >= sma60_cny`
- 触发规则 2：`close_price_cny >= breakout_level_cny`
- breakout 量能确认：当 breakout 被当作入场触发时，要求 `volume_ratio_20d >= min_breakout_volume_ratio`，默认下限 `1.2`
- 回踩支撑确认：`low_price_cny` 在 `SMA20` 容忍带内测试支撑，`close_price_cny >= sma20_cny`，且 `close_price_cny <= prev_close_price_cny`
- 回踩量能约束：当 supported pullback 被当作入场触发时，要求 `volume_ratio_20d <= max_pullback_volume_ratio`，默认上限 `1.0`
- 不追高保护：`close_price_cny <= sma20_cny * (1 + max_close_above_sma20_ratio)`，默认上限 `5%`
- 透明分数：
  - `candidate_band=2`
  - `watch_band=1`
  - `close>=sma20=1`
  - `sma20>=sma60=1`
  - `confirmed_sma20_cross=1`
  - `breakout_confirmation=1`
  - `breakout_volume_confirmation=1`
  - `supported_pullback_confirmation=1`
  - `pullback_volume_contraction=1`
  - `no_chase_guard=1`
  - 满分 `10`

当前分类逻辑：

- `candidate`：市值进入 `candidate_band`，趋势双确认通过，且满足下列任一路径，同时不过度偏离 `SMA20`
  - `SMA20/SMA60` 金叉确认
  - `breakout_level` 突破确认，并且 `volume_ratio_20d` 达到量能下限
  - `SMA20` 支撑回踩确认，并且 `volume_ratio_20d` 没有高于回踩量能上限
- `watch`：市值至少进入 `watch_band`，但仍有任一候选条件未满足，例如：
  - 只在 `watch_band`
  - 趋势过滤未通过
  - 缺少金叉 / breakout / supported pullback 触发确认
  - breakout 已出现，但缺少量能确认或量能不足
  - 回踩支撑已出现，但缺少量能收敛上下文，或回踩伴随放量压力
  - 回踩过程中跌破 / 明显下刺 `SMA20`，触发风险降级
  - 触发满足但触发后已经过度偏离 `SMA20`，触发“不追高”降级
- `reject`：缺少市值快照，或市值低于 `watch_band`

当前扫描输出除了主 `reason` 之外，还会附带两组显式解释字段：

- `signal_reasons`：已经成立的正向确认码，例如 `breakout_volume_confirmed`
- `risk_flags`：导致降级、等待或拒绝的风险 / 缺口码，例如 `pullback_volume_above_threshold`

说明：

- 当前 scanner 读取的是“已经算好的技术快照 CSV”，不会自己抓取历史 K 线，也不会在仓库内回补真实行情
- 技术快照允许部分字段留空；缺失字段会显式体现为 `missing` 规则状态
- 旧版最小技术快照（只有 `close/sma20/sma60`）仍然兼容，但在当前阶段规则下通常只能进入 `watch`，直到补齐触发确认所需的上下文
- `volume_ratio_20d` 当前只服务于 breakout / pullback 质量确认，不会把项目扩展成自动量化执行系统
- 统一归一化后再扫描：市值用 `billion_cny`，技术数值用 `cny`
- 后续如接入 Tushare / Akshare / 其他 provider，只需先适配到这两份标准 CSV 合约
- 这仍然只是决策支持输出，不是自动交易系统

## 目录结构

- `scripts/refresh_stock_list.py`
- `scripts/build_stock_index.py`
- `scripts/refresh_market_cap_snapshot.py`
- `scripts/refresh_technical_snapshot.py`
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
