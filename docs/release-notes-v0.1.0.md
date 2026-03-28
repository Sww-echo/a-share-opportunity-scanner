# Release Notes — v0.1.0

## Summary
This release marks the MVP freeze of the lightweight A-share opportunity scanner.

The project now provides:
- a rule-driven decision-support scanner for A-shares
- explicit candidate / watch / reject classification
- transparent scoring, signal reasons, and risk flags
- ranked outputs for daily review
- human-readable text summary output in addition to CSV / JSON artifacts
- sample/csv end-to-end flows
- technical snapshot generation from OHLCV CSV inputs

## Included capabilities
### Core architecture
- stock list layer
- universe builder layer
- market-cap snapshot contract
- technical snapshot contract
- scanner / ranking / formatter layers

### Scanner semantics
- trend confirmation (`close >= SMA20`, `SMA20 >= SMA60`)
- SMA20/SMA60 crossover confirmation
- breakout confirmation
- breakout volume confirmation
- supported pullback confirmation
- pullback volume contraction
- pullback freshness
- no-chase guard
- circulating market cap liquidity proxy
- breakout failure / reset semantics
- crossover price confirmation semantics

### Output / review
- CSV outputs
- JSON summary outputs
- text review summary (`Daily Scan Review`)
- ranking within decision buckets

### Engineering maturity
- modularized scanner internals
- scanner config layer
- tests for scanner, ranking, formatter, config, and technical OHLCV pipeline
- project docs for system architecture, rule mapping, remaining work, and code gaps

## Explicit non-goals in v0.1.0
- automatic trading execution
- LLM final decision-making
- notifications / UI / scheduling platform features
- fully solved real-data provider coverage for all fact layers

## Known limitations
- real stock list refresh via Tushare `stock_basic` works with the current token
- real market-cap snapshot refresh is not complete because current token lacks `trade_cal` / `daily_basic` permissions
- real technical snapshot generation currently depends on local/CSV OHLCV input, not a fully automated daily provider chain

## Recommended next phase
1. real/fallback market-cap snapshot provider
2. stronger technical snapshot provider chain
3. ranking and output polish as needed for daily use
4. later runtime cutover (cron / skill) to this project as the primary scanner
