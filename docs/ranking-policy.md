# Scanner 排序层说明

## 目标
当前 scanner 已经能输出：
- `candidate`
- `watch`
- `reject`
- `score`
- `reason`
- `signal_reasons`
- `risk_flags`

本轮新增的排序层，不改变分类规则本身，只负责把同一批扫描结果按“更适合人工复核”的顺序排好。

排序实现位于：
- `src/scanner/ranking.py`

测试位于：
- `tests/test_ranking.py`
- `tests/test_scanner.py`

---

## 排序原则
排序只使用当前已经存在的 fact/rule 输出，不引入新的指标或隐式打分。

当前排序维度按先后顺序如下：

1. `decision`
   - `candidate` 优先于 `watch`
   - `watch` 优先于 `reject`

2. `major risk tier`
   - 先看是否存在 hard blocker / reset / 结构性损伤
   - 这一层放在 `score` 前面，避免“高分但已坏形”的 `watch` 排到过前面

3. `score`
   - 在相同 `decision`、相同风险层级内，分数高的优先

4. confirmed trigger 数量
   - 同分时，独立确认触发越多越优先

5. confirmed trigger 语义优先级
   - `supported_pullback`
   - `volume_backed_breakout`
   - `confirmed_crossover`

6. trigger freshness / quality
   - 使用当前已有规则状态进一步区分：
   - crossover 是否是 fresh cross、是否缺价格确认
   - breakout 是否是 fresh breakout、是否缺量、是否已 stale、是否 failed
   - pullback 是否是 fresh supported pullback、是否缺量、是否已 rebounded too far

7. `risk_flags` 数量
   - 在前面维度仍相同时，风险标记更少的优先

8. 流动性代理
   - `circulating_market_cap_billion_cny` 更大的优先
   - 仍相同则比较 `total_market_cap_billion_cny`

9. `symbol`
   - 最后用代码做稳定 tie-break

---

## 当前 major risk tier 语义

### Tier 0
无明显降级风险，或只是普通等待状态。

### Tier 1
确认缺口 / 上下文缺失，例如：
- breakout 缺量确认
- crossover 缺价格确认
- 技术上下文缺失

### Tier 2
已不够新鲜，或仍停留在 watch-band / liquidity watch-band，例如：
- `stale_above_breakout`
- pullback 已经反弹离 `SMA20` 太远
- 总市值只在 `watch_band`
- 流通市值只在 `watch_band` 或缺失

### Tier 3
存在结构性损伤或明显不宜追价，例如：
- `close < sma20`
- `sma20 < sma60`
- `undercut_sma20_support`
- `closed_below_sma20`
- `overextended`

### Tier 4
存在 hard blocker / reset 级别问题，例如：
- `failed_breakout`
- 总市值低于 `watch_band`
- 流通市值低于 `watch_band`
- 缺失市值快照

---

## trigger 语义为什么这样排

### supported pullback
当前排在单一触发里最高，是因为它同时代表：
- 趋势仍在
- 价格重新靠近 `SMA20`
- 风险收益比通常更可控

### volume-backed breakout
排在第二，是因为它具备：
- fresh 价格突破
- 显式量能确认

但相对 supported pullback，通常更接近“不追高”边界，因此放在其后。

### confirmed crossover
排在第三，是因为它说明趋势关系刚改善，但本身通常还弱于：
- 已经完成量能确认的 breakout
- 已经在 `SMA20` 获得支撑的 fresh pullback

---

## 当前明确会被压后的情形

- `failed_breakout`
- `stale_above_breakout`
- pullback 已不 fresh
- `overextended`
- 流通市值不足或只在 watch-band
- 同类 setup 下 `risk_flags` 更多

这意味着：
- 一个高分但带 `failed_breakout` reset 语义的 `watch`
- 不会排在一个更干净、只是缺量确认的 breakout watch 前面

---

## 边界
当前排序层仍然是：
- 显式
- 可测试
- 可复现

它不会：
- 引入 UI
- 引入通知
- 引入调度
- 引入 LLM 决策
- 引入交易执行

---

## 下一步建议
如果继续遵循“先不做 snapshot-layer 扩张”的前提，排序层之后最合适的增量是：

1. `WP3` 风险降级细化
   - failed breakout reset / 冷却期
   - crossover freshness 继续细化
   - supported pullback 质量分层继续细化

2. `WP4` formatter / 输出层
   - Top N candidate/watch 摘要
   - 更短的主结论
   - 风险与正向信号分开展示
