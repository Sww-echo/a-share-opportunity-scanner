# 当前缺口与下一步优先级

## 1. 当前整体状态
项目主体（轻量决策支持扫描器）已经完成第一阶段与第二阶段核心建设：
- 股票列表层已建立
- universe 构建层已建立
- 市值快照层与技术快照层契约已建立
- scanner 已支持 candidate / watch / reject
- 已实现趋势、金叉、突破、量能确认、supported pullback、不追高等规则
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

#### 未完成
这些字段目前主要依赖：
- sample
- csv
- 人工准备的事实输入

尚未完成：
> 从真实 OHLCV 数据自动推导并生成 technical snapshot

#### 影响
没有真实 technical snapshot，scanner 虽然能跑，但仍主要处于“结构已成、真实技术事实未完全打通”的状态。

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

### P1：结果排序与人工复核体验
#### 当前已有
- `score`
- `reason`
- `signal_reasons`
- `risk_flags`
- `candidate/watch/reject`

#### 未完成
- 更精细的候选排序逻辑
- 同分情况下的优先级解释
- 更适合人看的中文摘要
- 对“为什么只是 watch 不是 candidate”的更直接表述

#### 目标
让输出不仅“工程上可读”，也“交易复核时可直接使用”。

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
优化结果排序、候选说明、风险表达

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
