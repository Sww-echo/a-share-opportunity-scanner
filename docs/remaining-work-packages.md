# 剩余工作包（最后 20%）

## 总体判断
当前项目核心规则引擎已经接近完成，剩余工作主要集中在：
1. 真实 technical snapshot 自动生成
2. 少量风险细化
3. 结果呈现优化
4. 新项目正式接管运行入口

当前阶段不再属于“从 0 到 1”，而是从“像样 MVP”推进到“接近可日用初版”。

---

## WP1：真实 technical snapshot 自动生成（最高优先级）
### 目标
把当前 sample/csv 形式的 technical snapshot，升级成可由真实 OHLCV 自动生成。

### 最小实现目标
至少支持自动生成以下字段：
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

### 产出建议
- `scripts/refresh_technical_snapshot_from_ohlcv.py`
- `src/technical/calculators.py`
- `src/technical/ohlcv_provider.py`

### 备注
即使一开始只支持 csv/本地 OHLCV，也值得先做，因为这能把规则引擎与真实技术事实真正打通。

---

## 已完成：WP2 候选排序层
当前已经落地：
- `src/scanner/ranking.py`
- `tests/test_ranking.py`
- scanner summary 中的 `ranking_model`

当前排序层已经明确支持：
- `candidate/watch/reject` 分层排序
- major risk / reset 先于 `score` 的降级
- breakout / crossover / pullback 三类触发语义优先级
- freshness / quality 参与排序
- `risk_flags` 数量与流动性代理参与 tie-break

详细规则见 [docs/ranking-policy.md](/root/.openclaw/workspace/projects/a-share-opportunity-scanner/docs/ranking-policy.md)。

---

## WP3：风险降级细化（第三优先级）
### 目标
继续把已存在的结构信号做得更稳，不盲目扩大指标范围。

### 候选项
- crossover freshness 继续细化
- failed breakout 冷却期 / reset 语义强化
- supported pullback 质量继续细分
- 流动性过滤更明确（如果事实层支持）

### 备注
这一块应继续保持“少量、显式、可测试”，不要回到大而全策略堆叠。

---

## WP4：结果输出优化（第四优先级）
### 目标
让结果更适合人工复核和日常使用。

### 最小实现目标
- 输出 Top N candidate/watch
- 每条结果提供更短的主结论
- 风险点与正向信号分开展示
- summary 更像日报摘要

### 产出建议
- `src/scanner/formatter.py`
- 更适合人看的 CLI 输出模式
- JSON/CSV 保持不变，新增简洁文本模式

---

## WP5：新项目正式接管运行入口（后置）
### 目标
把定时任务、交互调用逐步迁移到新项目。

### 条件
该工作包应在以下条件满足后再做：
- technical snapshot 自动生成打通
- 基础排序层可用
- 结果输出足够稳定

### 备注
当前不应急于上线切换，先把 scanner 主体做扎实。

---

## 推荐实施顺序
1. WP1：真实 technical snapshot 自动生成
2. WP3：风险降级细化
3. WP4：结果输出优化
4. WP5：新项目接管正式运行入口

如果当前继续按产品策略暂缓 snapshot-layer 扩张，则下一步最合适的是：
1. WP3：风险降级细化
2. WP4：结果输出优化

---

## 一句话总结
项目剩余工作已经集中在“真实技术事实 + 风险细化 + 输出体验”三个方向。
规则引擎本身已经相对成熟，不需要再大规模改方向。
