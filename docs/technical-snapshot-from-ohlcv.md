# Local OHLCV To Technical Snapshot

## 目标

当前仓库已经支持把本地 `OHLCV` 风格 CSV 直接转换成 scanner 可消费的标准化 technical snapshot CSV。

这条链路仍然严格停留在“事实准备层”：

- 只生成技术事实
- 不自动下单
- 不把 scanner 变成历史行情抓取平台

---

## 输入合约

脚本入口：

```bash
python3 scripts/refresh_technical_snapshot_from_ohlcv.py --input /path/to/ohlcv.csv
```

当前支持的本地 CSV 列如下。

必需列：

- `ts_code`
- `trade_date` 或 `date`
- `high` 或 `high_price_cny`
- `low` 或 `low_price_cny`
- `close` 或 `close_price_cny`

可选列：

- `symbol` 或 `code`
- `name`
- `volume` / `vol` / `volume_shares` / `turnover_volume`

说明：

- `trade_date` 会被归一化成 `YYYYMMDD`
- 每个 `ts_code` 会按日期排序
- 同一股票同一日期如果出现重复行，会直接报错
- 如果没有 volume 列，`volume_ratio_20d` 会留空，scanner 会把相关确认降级为 `missing`

---

## 当前计算语义

输出字段与 scanner 现有契约保持一致：

- `close_price_cny`：最新一日收盘价
- `prev_close_price_cny`：前一日收盘价
- `low_price_cny`：最新一日日内低点
- `sma20_cny`：最近 20 个收盘价均值
- `sma60_cny`：最近 60 个收盘价均值
- `prev_sma20_cny`：上一交易日对应的 20 日均线
- `prev_sma60_cny`：上一交易日对应的 60 日均线
- `breakout_level_cny`：不含最新日的前 20 个交易日最高价
- `volume_ratio_20d`：最新成交量 / 前 20 个交易日平均成交量
- `as_of_date`：最新交易日

窗口不足时：

- `sma20_cny` 需要至少 20 行
- `sma60_cny` 需要至少 60 行
- `prev_sma20_cny` 需要至少 21 行
- `prev_sma60_cny` 需要至少 61 行
- `breakout_level_cny` 需要至少 21 行
- `volume_ratio_20d` 需要至少 21 行且有 volume

---

## 使用方式

先把本地 OHLCV 转成标准 technical snapshot：

```bash
python3 scripts/refresh_technical_snapshot_from_ohlcv.py \
  --input /path/to/ohlcv.csv \
  --output /tmp/technical_snapshot_cn.csv
```

再用已有扫描入口消费该快照：

```bash
python3 scripts/run_daily_scan.py --technical-input /tmp/technical_snapshot_cn.csv
```

如果要跑当前端到端 flow，仍然保持两步：

1. 先生成 technical snapshot CSV
2. 再把它作为 `--technical-provider csv --technical-input ...` 传给 `scripts/run_rule_based_flow.py`

这样做是刻意保持当前架构轻量，不把“一键 flow”直接扩展成历史行情抓取/缓存编排系统。

---

## 这次增量真正变成了什么

已经变成真实/本地事实链路的部分：

- technical snapshot 不再只能依赖预制 sample snapshot 行
- scanner 依赖的核心技术字段现在可以由本地 OHLCV 历史自动计算
- 本地 CSV 输入可以直接产出与现有 scanner 契约一致的技术快照

仍然没有进入这次增量的部分：

- 仓库内自动抓取远程 OHLCV
- technical provider 的在线 fallback / 缓存策略
- `run_rule_based_flow.py` 直接吃原始 OHLCV 并代替预处理步骤
- 更复杂的平台压力位识别、成交额/换手率扩展、更多技术指标
