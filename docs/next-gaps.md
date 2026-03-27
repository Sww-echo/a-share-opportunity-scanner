# 当前缺口与下一步优先级

## 1. 当前整体状态
项目主体（轻量决策支持扫描器）已经完成第一阶段与第二阶段核心建设：
- 股票列表层已建立
- universe 构建层已建立
- 市值快照层与技术快照层契约已建立
- scanner 已支持 candidate / watch / reject
- 已实现趋势、金叉、突破、量能确认、supported pullback、不追高等规则
- 已实现独立排序层与 ranking tests
- 已具备 sample/csv 端到端 flow 与测试

当前项目已经是一个**可运行的轻量规则扫描器 MVP**，不是空壳，也不是纯设计稿。

---

## 2. 关键缺口（按优先级排序）

### P0：真实 technical snapshot 自动生成
这是当前最核心的缺口。

#### 已有
当前 technical snapshot 契约已支持：
- `close_price_cny`
- `prev_close_price_cny`
- `low_price_cny`
- `sma20_cny`
- `sma60_cny`
- `prev_sma20_cny`
- `prev_sma60_cny`
- `breakout_level_cny`
- `volume_ratio_20d`

本轮已新增一条最小真实链路：

- `scripts/refresh_technical_snapshot_from_ohlcv.py`
- 本地 OHLCV CSV -> 标准 technical snapshot CSV
- `close / prev_close / low / SMA20 / SMA60 / prev SMA20 / prev SMA60 / breakout level`
- `volume_ratio_20d` 在输入包含 volume 时可自动计算

#### 未完成
这些字段已经不再只依赖预制 sample snapshot 行，但仍未完成：

- 仓库内自动抓取远程 OHLCV
- 更稳定的 technical provider 组合 / fallback
- 让一键 flow 直接吃原始 OHLCV 而不经过预处理步骤

#### 影响
本地真实 OHLCV 已经可以把 scanner 主体和技术事实打通，但“可日更、可自动供应”的真实技术事实层仍未完全补齐。

---

### P0：真实市值快照来源
#### 已确认状态
- `stock_basic`：已通过 Tushare token 真实跑通 ✅
- `trade_cal`：权限不足 ❌
- `daily_basic`：权限不足 ❌

#### 结论
当前 token 可以承担：
- 真实股票列表刷新

但不能承担：
- 真实市值快照刷新

#### 影响
没有真实市值快照时：
- 项目仍可运行
- 但“按真实最新市值 > 100 亿”做日更筛选尚未完全成立

#### 下一步方向
- 寻找替代市值源
- 或更高权限 token
- 或暂以本地快照 / CSV 作为事实输入兜底

---

### P1：真实 provider 组合与 fallback 策略
#### 当前已有
- sample/csv provider
- Tushare 股票列表真实路径
- provider 抽象架构

#### 未完成
- 市值 provider 的替代/组合方案
- technical provider 的真实来源
- provider 失败时的自动 fallback
- 更稳定的真实事实层供应链

#### 目标
让事实层不是单点依赖，而是：
- 主 provider 可用时优先使用
- 不可用时自动 fallback 到可接受的替代源/缓存

---

### P1：复核输出的跨日对比 / blocker 聚合
#### 当前已有
- `score`
- `reason`
- `signal_reasons`
- `risk_flags`
- `candidate/watch/reject`
- 独立排序层
- `ranking_model`
- text formatter / human-readable review 输出

#### 未完成
- 同一标的相对上一轮扫描的状态变化摘要
- watch/reject bucket 中 blocker 的更强聚合视图
- 更直接回答“为什么还是 watch / 为什么被打回 reject”的批量归因对比

#### 目标
让人工复核不仅能看“当前排序结果”，也能快速看出“今天相对昨天发生了什么变化”。

---

### P2：上线运行切换
#### 当前状态
- 新项目已经具备主体能力
- 但日常运行入口（定时任务 / skill / 交互链路）尚未完全切到新项目

#### 未完成
- cron 迁移到新项目
- skill 调用指向新项目
- 新旧原型职责彻底切分

#### 目标
让 `a-share-opportunity-scanner` 成为正式主项目。

---

## 3. 现在“不缺”的部分
这些不是当前主要缺口：
- 项目结构
- 决策机制边界
- candidate/watch/reject 规则框架
- 第二阶段核心规则（趋势/触发/量能/回踩/不追高）
- sample/csv 端到端 flow
- 文档与测试基础

也就是说：
> 当前的瓶颈已经不是“项目不会做”，而是“真实事实层还没完全补齐”。

---

## 4. 推荐下一步顺序
### Step 1
优先解决真实 technical snapshot 自动生成

### Step 2
补真实市值快照替代源 / fallback 方案

### Step 3
如果继续暂缓 snapshot-layer 扩张，优先做风险降级细化与跨日 diff 复核

### Step 4
把定时任务 / skill / 日常交互切到新项目

---

## 5. 一句话总结
当前项目已经是一个：

> **规则驱动、可解释、可测试的轻量决策支持扫描器 MVP**

现在最关键的未完成项，不是规则框架，而是：
- 真实 technical snapshot
- 真实市值快照
- 真实事实层的稳定供应链
- 风险细化与跨日人工复核
