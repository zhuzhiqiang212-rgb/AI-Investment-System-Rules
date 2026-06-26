# 投资决策证据链估值锚 V1.0 数据包

- 数据日期: 2026-06-26
- 生成时间: 2026-06-26 11:29:40 JST
- 边界: 只做数据，不写产品正文，不下投资建议。

## NVDA
```json
{
  "ticker": "US.NVDA",
  "current_realtime_price": {
    "value": 195.74,
    "currency": "USD",
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-25 22:29:35.655"
  },
  "consensus_eps": {
    "2026": "缺失",
    "2027": "缺失",
    "reason": "未取得可验证的开放一致预期EPS数据库字段"
  },
  "current_forward_pe": {
    "value": 19.34,
    "source": "Barron's news snippet, 2026-06-25; not a direct data-vendor consensus feed",
    "source_url": "https://www.barrons.com/articles/-why-nvidia-stock-is-not-going-up-b16d975d"
  },
  "futu_valuation_snapshot": {
    "pe_ratio": 39.946,
    "pe_ttm_ratio": 29.975,
    "pb_ratio": 24.234,
    "earning_per_share_ttm_or_snapshot": 4.9,
    "total_market_val": 4736908000000.0,
    "issued_shares": 24200000000,
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-25 22:29:35.655"
  },
  "past_5y_pe_range_or_percentile": {
    "value": "缺失",
    "reason": "未取得5年PE历史序列/分位；Futu快照仅提供当前PE/TTM PE"
  },
  "moving_averages": {
    "ma50": 210.2128,
    "ma100": 196.1671,
    "ma200": 190.5314,
    "currency": "USD",
    "source": "Yahoo chart 1y daily close",
    "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/NVDA?range=1y&interval=1d"
  },
  "major_consensus_target_price_range": {
    "value": "缺失",
    "reason": "未取得实时一致目标价区间数据库",
    "public_examples_not_consensus": [
      {
        "target": 240,
        "firm": "Morningstar",
        "source": "Business Insider 2025-11"
      },
      {
        "target": 250,
        "firm": "Jefferies",
        "source": "Business Insider 2025-11"
      },
      {
        "target": 255,
        "firm": "Truist",
        "source": "Business Insider 2025-11"
      },
      {
        "target": 320,
        "firm": "Melius Research",
        "source": "Business Insider 2025-11"
      },
      {
        "average_target": 267.69,
        "source": "Barron's 2026-03 snippet"
      }
    ]
  },
  "data_sources_and_time": [
    "Futu OpenD snapshot",
    "Yahoo chart fetched at 2026-06-26 11:29:40 JST",
    "Barron's / Business Insider public news snippets"
  ]
}
```

## SoftBank_9984
```json
{
  "ticker": "JP.9984",
  "current_realtime_price": {
    "value": 6249.0,
    "currency": "JPY",
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-26 11:29:38"
  },
  "current_market_cap": {
    "value": 35693338901880.0,
    "currency": "JPY",
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-26 11:29:38"
  },
  "arm_stake": {
    "arm_current_price": 347.71,
    "arm_market_cap": 371381665639.6,
    "arm_issued_shares": 1068078760,
    "softbank_arm_ownership_pct": {
      "value": 87.1,
      "source": "Wikipedia/compiled public profile snippet; exact latest ownership not verified by official filing in this run"
    },
    "softbank_arm_shares_held": "缺失",
    "softbank_arm_stake_market_value": "缺失",
    "reason_missing_exact_shares": "未取得官方最新持股数量；不按比例反推作正式字段"
  },
  "vision_fund_or_latest_nav_composition": {
    "value": "缺失",
    "public_context": [
      "FT 2026-06-26 snippet: Arm and OpenAI make up about two-thirds of NAV.",
      "MarketWatch 2026-02 snippet: OpenAI stake around 11%; fiscal third-quarter portfolio valuation 30.9T yen, later 33.1T yen; article cited 19% discount to NAV at that time."
    ],
    "reason": "未取得官方结构化NAV组成表/每股NAV，本轮不反推"
  },
  "net_debt": {
    "value": "缺失",
    "public_context": "FT 2026-06-26 snippet references ¥18T debt burden, but not used as official net debt field.",
    "reason": "未取得官方净债务口径表"
  },
  "nav_per_share_estimate": {
    "value": "缺失",
    "reason": "未取得官方每股NAV；不根据新闻折价比例反推"
  },
  "current_price_discount_or_premium_to_nav": {
    "value": "缺失",
    "public_context": [
      "FT 2026-06-26 snippet: market at about 50% discount to NAV.",
      "MarketWatch 2026-02 snippet: article cited 19% discount to NAV at that time."
    ],
    "reason": "本轮未取得官方NAV基准，无法计算当前折价/溢价"
  },
  "historical_discount_range": {
    "value": "缺失",
    "reason": "未取得历史NAV折价序列"
  },
  "moving_averages": {
    "ma50": 6343.56,
    "ma100": 5145.91,
    "ma200": 4950.9388,
    "currency": "JPY",
    "source": "Yahoo chart 1y daily close",
    "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/9984.T?range=1y&interval=1d"
  },
  "data_sources_and_time": [
    "Futu OpenD snapshot",
    "Yahoo chart fetched at 2026-06-26 11:29:40 JST",
    "FT / WSJ / MarketWatch / public profile snippets"
  ]
}
```

## MSTR
```json
{
  "ticker": "US.MSTR",
  "current_realtime_price": {
    "value": 85.33,
    "currency": "USD",
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-25 22:29:39.457"
  },
  "btc_current_realtime_price": {
    "value": 58770.98,
    "currency": "USD",
    "source": "Yahoo chart BTC-USD",
    "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1y&interval=1d",
    "source_time": "2026-06-26 11:29:40 JST"
  },
  "mstr_btc_holdings": {
    "value": 818334,
    "unit": "BTC",
    "source": "Barron's May 2026 snippet reporting Strategy held 818,334 BTC as of May 1, 2026",
    "source_url": "https://www.barrons.com/articles/strategy-loss-bitcoin-dd50fe8b"
  },
  "mstr_market_cap": {
    "value": 29903716917.76,
    "currency": "USD",
    "source": "Futu OpenD get_market_snapshot",
    "source_time": "2026-06-25 22:29:39.457"
  },
  "debt_or_convertible_balance": {
    "value": "缺失",
    "public_context": [
      "IBD 2026-06-26 snippet: up to $7.9B obligations by 2028; $4.5B convertible bonds potentially needing early repayment."
    ],
    "reason": "未解析SEC原文债务表，不能给完整债务余额字段"
  },
  "mnav": {
    "formula": "market_cap / (btc_holdings * btc_price)",
    "btc_holdings_value_usd": 48094291147.32,
    "value": 0.621773,
    "source_inputs": [
      "Futu OpenD MSTR market cap",
      "Yahoo BTC-USD",
      "Barron's reported BTC holdings"
    ]
  },
  "past_mnav_range": {
    "value": "缺失",
    "reason": "未取得历史mNAV序列"
  },
  "btc_key_support_levels": {
    "source": "Yahoo BTC-USD daily chart technical anchors",
    "ma50": 70611.9473,
    "ma100": 71836.6595,
    "ma200": 76149.6075,
    "recent_90d_low": 58770.9805,
    "recent_180d_low": 58770.9805,
    "note": "这是技术锚，不是交易建议。"
  },
  "moving_averages_mstr": {
    "ma50": 151.7692,
    "ma100": 142.1148,
    "ma200": 187.184,
    "currency": "USD",
    "source": "Yahoo chart 1y daily close",
    "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/MSTR?range=1y&interval=1d"
  },
  "data_sources_and_time": [
    "Futu OpenD snapshot",
    "Yahoo chart fetched at 2026-06-26 11:29:40 JST",
    "Barron's / IBD public news snippets"
  ]
}
```

## Sources
- Futu OpenD local quote snapshot: local:127.0.0.1:11111
- Yahoo Finance chart NVDA: https://query1.finance.yahoo.com/v8/finance/chart/NVDA?range=1y&interval=1d
- Yahoo Finance chart 9984.T: https://query1.finance.yahoo.com/v8/finance/chart/9984.T?range=1y&interval=1d
- Yahoo Finance chart MSTR: https://query1.finance.yahoo.com/v8/finance/chart/MSTR?range=1y&interval=1d
- Yahoo Finance chart BTC-USD: https://query1.finance.yahoo.com/v8/finance/chart/BTC-USD?range=1y&interval=1d
- Barron's NVDA forward PE snippet: https://www.barrons.com/articles/-why-nvidia-stock-is-not-going-up-b16d975d
- Business Insider NVDA target examples: https://www.businessinsider.com/nvidia-stock-price-prediction-nvda-earnings-q3-jensen-huang-bubble-2025-11
- FT SoftBank NAV discount snippet: https://www.ft.com/content/1daf6066-885e-4acd-bda9-c51d85587875
- MarketWatch SoftBank OpenAI/NAV snippet: https://www.marketwatch.com/story/softbank-says-it-made-4-2-billion-from-its-openai-investment-in-the-last-quarter-27988734
- Barron's Strategy BTC holdings snippet: https://www.barrons.com/articles/strategy-loss-bitcoin-dd50fe8b
- IBD Strategy obligations snippet: https://www.investors.com/news/mstr-stock-bitcoin-whale-strategy-cash-reserve-strc-preferred-stock/