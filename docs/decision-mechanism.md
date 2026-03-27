# 决策机制设计稿

## 1. 系统定位
本系统是**决策支持系统**，不是自动交易执行系统。

- 系统负责：筛选、评分、风险提示、解释
- 用户负责：最终买入/卖出决策
- LLM 负责：解释，不直接拍板交易

## 2. 决策分层
### 2.1 数据事实层
负责提供原始事实：
- 股票列表
- 市值/流通市值
- 技术快照（当前已实现字段：收盘价、前收、日内低点、SMA20、SMA60、前一日 SMA20/SMA60、breakout 参考位、`volume_ratio_20d`）
- K 线 / OHLCV（未来真实集成）
- 实时行情（未来）
- 换手率 / 量比（未来）
- 新闻 / 基本面 / 资金流（可选）

### 2.2 规则筛选层
完全规则化、可解释、可复现。

候选筛选示例：
- 市值 > 阈值（默认可配置）
- 非 ST
- 数据完整
- SMA(5/10) 金叉
- 收盘价站上 SMA20
- 可选 breakout

当前仓库已落地的规则不是上面的完整理想集，而是一个更小、可复现的子集：
- 市值进入 `candidate_band` 或 `watch_band`
- 收盘价是否站上 `SMA20`
- `SMA20` 是否高于 `SMA60`
- `SMA20` 是否刚刚上穿 `SMA60`
- 收盘价是否站上预先准备的 `breakout_level`
- 如果 breakout 被当作入场触发，`volume_ratio_20d` 是否达到配置下限
- 是否形成“回踩 `SMA20` 获得支撑”的显式事实
- 如果 supported pullback 被当作入场触发，`volume_ratio_20d` 是否没有高于回踩量能上限
- 是否触发“不追高”保护：收盘价不得显著高于 `SMA20`

输出：
- candidate
- watch
- reject

### 2.3 评分与操作建议层
对候选标的打分，而不是直接下单。

输出示例：
- A 级候选 / B 级候选 / C 级候选
- 低吸观察 / 等待确认 / 不追高 / 风险警示

### 2.4 解释层（LLM 可选）
LLM 只负责：
- 解释规则结果
- 总结风险点
- 生成自然语言报告

LLM 不负责：
- 单独决定买入卖出
- 触发自动下单

## 3. 最终拍板机制
第一阶段：由用户最终拍板。

系统仅输出：
1. 候选买入机会
2. 风险提示
3. 无操作建议

## 4. 第一版原则
1. 不自动下单
2. 不让 LLM 单独拍板
3. 规则引擎必须可复现、可测试
4. 每日没有高质量机会时，应明确输出“今日无高质量机会”
5. 当前规则只使用本地 CSV / 样例可喂入的事实，不依赖 token 驱动的推理 provider

## 4.1 当前实现的实际分类方式

- `candidate`：市值进入 `candidate_band`，`close >= sma20`、`sma20 >= sma60` 成立，且满足下列任一路径，同时不过度偏离 `SMA20`
  - `SMA20/SMA60` 金叉确认
  - `breakout_level` 突破确认并伴随 `volume_ratio_20d` 达标
  - `SMA20` 回踩支撑确认并伴随 `volume_ratio_20d` 不高于回踩上限
- `watch`：市值至少进入 `watch_band`，但技术趋势过滤、触发确认、回踩质量确认或“不追高”保护仍有缺口
- `reject`：缺少市值快照，或市值低于 `watch_band`

当前透明分数：

- `candidate_band = 2`
- `watch_band = 1`
- `close >= sma20 = 1`
- `sma20 >= sma60 = 1`
- `confirmed_sma20_cross = 1`
- `breakout_confirmation = 1`
- `breakout_volume_confirmation = 1`
- `supported_pullback_confirmation = 1`
- `pullback_volume_contraction = 1`
- `no_chase_guard = 1`
- 满分 `10`

说明：

- 这个分数当前用于排序和解释，不会触发自动交易
- 当前技术规则来自外部准备好的技术快照 CSV，而不是仓库内自动回算整段价格历史
- 旧版只含 `close/sma20/sma60` 的技术快照仍兼容，但在当前阶段规则下会因为缺少触发确认上下文而更倾向进入 `watch`
- breakout / pullback 的量能确认当前只消费已准备好的 `volume_ratio_20d` 事实，不会在仓库内引入新的付费行情权限或自动执行逻辑
- 当前输出除了主 `reason` 之外，还会额外返回 `signal_reasons` 与 `risk_flags`，把候选确认与降级原因拆开表达

## 5. 后续演进
### 第二阶段
系统可输出：
- Buy Candidate
- Sell Warning
- Take Profit Watch
- Stop Loss Trigger

但仍不自动交易。

### 第三阶段（未来）
如需自动化交易，需新增：
- 仓位控制
- 风控
- 回测
- 审计日志
- 交易执行隔离层
