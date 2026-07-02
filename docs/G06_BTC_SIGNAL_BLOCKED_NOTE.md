# G-06 BTC信号 — 状态记录

状态: BLOCKED（付费API待接入）
更新时间: 2026-06-14 JST

## 根因
Yahoo Finance BTC-USD 和 CoinGecko 公开API
均返回 HTTP 429 Too Many Requests。
VIX / SPX / 10Y 使用指数代码不受影响。

## 用户决策
以后数据要准确，下一步可以付费。

## 待接入选项（用户选择后 Claude 发起任务）

选项A: CoinGecko Pro
  月费: 约 $29/月（Demo Plan）
  获取方式: https://www.coingecko.com/en/api/pricing
  API Key 接入位置: fetch_btc_change() 请求头
  优点: 同一代码库，改动最小

选项B: Binance 公开API（免费，无需账户）
  URL: https://api.binance.com/api/v3/ticker/24hr?symbol=BTCUSDT
  返回字段: priceChangePercent（24小时涨跌幅）
  优点: 完全免费，无需API Key，无429问题
  注意: 部分地区可能需要VPN

## 下一步
用户确认选项A或B后，Claude 发起修复任务。
在此之前，系统以3维运行（置信度B级），不影响日常使用。
