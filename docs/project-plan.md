# 项目规划

## 目标
构建一个轻量、可维护的 A 股机会扫描系统：
- 股票池更新
- 市值过滤
- 技术扫描
- 透明评分
- 人工复核友好的结果输出

## 模块规划
- 已完成
  - `scripts/refresh_stock_list.py`
  - `scripts/build_stock_index.py`
  - `scripts/refresh_market_cap_snapshot.py`
  - `scripts/refresh_technical_snapshot.py`
  - `scripts/run_daily_scan.py`
  - `src/data_provider/`
  - `src/market_cap/`
  - `src/universe/`
  - `src/scanner/`
  - `src/technical/`
  - 第二阶段 scanner 规则：
    - 市值 `candidate/watch` 带宽
    - `close >= SMA20`
    - `SMA20 >= SMA60`
    - `SMA20/SMA60` 金叉确认
    - breakout 确认
    - breakout 量能确认（基于准备好的 `volume_ratio_20d`）
    - `SMA20` supported pullback 确认（基于 `prev_close_price_cny` + `low_price_cny`）
    - pullback 量能约束
    - 不追高保护
- 后续候选
  - 真实 `OHLCV` / 指标事实层
  - 更丰富的量价确认等下一批 scanner 规则
  - 在已实现的 `signal_reasons` / `risk_flags` 之上继续收敛人工复核语义
  - `openclaw-skill/`（如未来确有需要）

## 参考来源
- daily_stock_analysis-main：借鉴数据源层、股票列表脚本、策略组织方式
- backtrader-starter：保留已有扫描原型思路
