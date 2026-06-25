# TASK-014 V1.3 资产管理数据准备

- 数据日期: 2026-06-26
- 生成时间: 2026-06-26 00:43:19 JST
- 数据质量: PARTIAL
- JSON: C:\AI_Investment_System\reports\handoff\V1_3_Asset_Management_Data_2026-06-26.json

## 账户状态
- FUTU: realtime | stale=False | source=C:\AI_Investment_System\data\position_snapshot.json
- IBKR: stale_ocr_snapshot | stale=True | source=C:\Users\zhu20\OneDrive\文档\New project 2\tmp\gdoc_fix\ocr_out\ibkr_ocr.txt
- SBI: stale_ocr_snapshot | stale=True | source=C:\Users\zhu20\OneDrive\文档\New project 2\tmp\gdoc_fix\ocr_out\sbi_ocr.txt
- BitFlyer: stale_ocr_snapshot | stale=True | source=C:\Users\zhu20\OneDrive\文档\New project 2\tmp\gdoc_fix\ocr_out\bitflyer_ocr.txt

## 富途实时持仓
| 代码 | 名称 | 数量 | 成本价 | 当前价 | 市值原币 | 市值JPY | 盈亏 | 盈亏% | 占账户% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| JP.4568 | 第一三共 | 6500.0 | 2948.3846 | 2566.5 | 16682250.0 JPY | 16682250.0 | -2482250.0 | -12.950000000000001 | 10.0347 |
| JP.7832 | 万代南梦宫 | 500.0 | 4272.0 | 3731.0 | 1865500.0 JPY | 1865500.0 | -270500.0 | -12.659999999999998 | 1.1221 |
| JP.7974 | 任天堂 | 2000.0 | 8246.8 | 6859.0 | 13718000.0 JPY | 13718000.0 | -2775600.0 | -16.830000000000002 | 8.2517 |
| JP.8766 | 东京海上控股 | 600.0 | 4908.3333 | 6850.0 | 4110000.0 JPY | 4110000.0 | 1165000.0 | 39.56 | 2.4723 |
| JP.9984 | 软银集团 | 4100.0 | 3601.1585 | 7118.0 | 29183800.0 JPY | 29183800.0 | 14419050.0 | 97.66 | 17.5547 |
| US.AVGO | 博通 | 150.0 | 383.125 | 381.73 | 57259.5 USD | 9259677.3842 | -209.25 | -0.36 | 5.5699 |
| US.COIN | Coinbase | 200.0 | 228.899 | 146.12 | 29224.0 USD | 4725937.3881 | -16555.7 | -36.16 | 2.8428 |
| US.CRCL | Circle | 400.0 | 94.918 | 70.02 | 28008.0 USD | 4529292.854 | -9959.0 | -26.229999999999997 | 2.7245 |
| US.MSFT | 微软 | 500.0 | 411.275 | 356.5 | 178250.0 USD | 28825565.9538 | -27387.73 | -13.320000000000002 | 17.3392 |
| US.MSTR | Strategy | 700.0 | 181.267 | 87.18 | 61026.0 USD | 9868774.1256 | -65860.58 | -51.910000000000004 | 5.9363 |
| US.NVDA | 英伟达 | 780.0 | 116.426 | 195.62 | 152583.6 USD | 24674943.1992 | 61770.96 | 68.02 | 14.8425 |
| US.TSM | 台积电 | 1.0 | -23351.29 | 441.01 | 441.01 USD | 71317.6036 | 23792.3 | 0.0 | 0.0429 |

## 合并资产口径
```json
{
  "four_account_total_assets": {
    "value": "缺失",
    "reason": "IBKR/SBI/BitFlyer 当前只有旧OCR快照，非执行级结构化数据，不能合成精确四账户总资产"
  },
  "known_realtime_futu_total_assets_jpy": 166245019.49960002,
  "stale_ocr_indicative_total_assets_jpy": 67817591.47,
  "stale_ocr_components": [
    {
      "account": "IBKR",
      "source": "stale OCR",
      "value_jpy": 32776138.472,
      "confidence": "low_ocr"
    },
    {
      "account": "SBI",
      "source": "stale OCR",
      "value_jpy": 18326715.0,
      "confidence": "low_ocr"
    },
    {
      "account": "BitFlyer",
      "source": "stale OCR",
      "value_jpy": 16714738.0,
      "confidence": "low_ocr"
    }
  ],
  "total_cash": {
    "value": "缺失",
    "reason": "非富途账户现金为旧OCR或缺失，四账户总现金不可可靠合并",
    "futu_realtime_cash_jpy": 1950933.0
  },
  "cash_ratio_pct": 1.1735,
  "allocation_realtime_futu_only": {
    "by_market": [
      {
        "key": "JP",
        "market_value_jpy": 65559550.0
      },
      {
        "key": "US",
        "market_value_jpy": 81955508.51
      }
    ],
    "by_sector": [
      {
        "key": "AI 主线/半导体",
        "market_value_jpy": 92015304.14
      },
      {
        "key": "保险/金融",
        "market_value_jpy": 4110000.0
      },
      {
        "key": "加密/稳定币相关",
        "market_value_jpy": 19124004.37
      },
      {
        "key": "医药/防御",
        "market_value_jpy": 16682250.0
      },
      {
        "key": "游戏/消费",
        "market_value_jpy": 15583500.0
      }
    ],
    "by_time_horizon": [
      {
        "key": "中期",
        "market_value_jpy": 36375750.0
      },
      {
        "key": "波段",
        "market_value_jpy": 19124004.37
      },
      {
        "key": "长期",
        "market_value_jpy": 92015304.14
      }
    ],
    "us_stock_pct": 49.298,
    "jp_stock_pct": 39.4355,
    "crypto_pct": "缺失",
    "crypto_pct_reason": "BitFlyer为旧OCR快照，未纳入实时精确资产比例",
    "ai_main_pct": 55.3492
  },
  "single_largest_holding": {
    "code": "JP.9984",
    "name": "软银集团",
    "weight_pct": 17.5547
  },
  "largest_loss_holding": {
    "code": "JP.7974",
    "name": "任天堂",
    "pnl": {
      "value": -2775600.0,
      "currency": "JPY",
      "pct": -16.830000000000002,
      "today_value": 0.0,
      "today_change_pct_estimated_from_today_pl": 0.0
    }
  },
  "largest_gain_holding": {
    "code": "JP.9984",
    "name": "软银集团",
    "pnl": {
      "value": 14419050.0,
      "currency": "JPY",
      "pct": 97.66,
      "today_value": 0.0,
      "today_change_pct_estimated_from_today_pl": 0.0
    }
  },
  "has_leverage": true,
  "leverage_scope": "FUTU实时确认；其它账户缺失"
}
```

## 七标的反向PK数据
### US.NVDA
```json
{
  "code": "US.NVDA",
  "current_price": 210.69,
  "today_change_pct": 2.9513804055704806,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": "缺失",
    "pe_ttm": "缺失",
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "AI GPU/加速卡",
  "main_risk": "估值与AI资本开支预期过高风险；若AI需求/毛利率弱化，弹性回撤较大",
  "relation_to_existing_holdings": "现有富途大仓位，直接影响AI主线敞口",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 211.6810179811,
    "ma20_dist_pct": -0.4681657290539376,
    "ma50": 209.12096217568,
    "ma50_dist_pct": 0.7503015517889011,
    "ma200": 189.68438974436998,
    "ma200_dist_pct": 11.073979405442081
  },
  "financial": {
    "fcf": "缺失",
    "debt_ratio": "缺失",
    "gross_margin": "缺失"
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.AVGO
```json
{
  "code": "US.AVGO",
  "current_price": 411.35,
  "today_change_pct": 4.695851361669656,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": "缺失",
    "pe_ttm": "缺失",
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "AI ASIC/网络/半导体",
  "main_risk": "AI ASIC预期、并购整合和高估值拥挤风险",
  "relation_to_existing_holdings": "现有富途持仓，AI硬件链补充敞口",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 413.73699999999997,
    "ma20_dist_pct": -0.5769365563147444,
    "ma50": 411.67400000000004,
    "ma50_dist_pct": -0.07870305144361822,
    "ma200": 359.15717308929,
    "ma200_dist_pct": 14.532029657593505
  },
  "financial": {
    "fcf": "缺失",
    "debt_ratio": "缺失",
    "gross_margin": "缺失"
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.CRDO
```json
{
  "code": "US.CRDO",
  "current_price": 271.83,
  "today_change_pct": 9.024184815305002,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": 37.966,
    "pe_ttm": 108.298,
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "AI连接/高速互联",
  "main_risk": "高成长高估值，订单兑现与客户集中风险",
  "relation_to_existing_holdings": "非当前富途持仓；与AI/半导体主线相关",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 231.83649999999997,
    "ma20_dist_pct": 17.25073489290945,
    "ma50": 197.32829999999998,
    "ma50_dist_pct": 37.75520287764096,
    "ma200": 153.604825,
    "ma200_dist_pct": 76.96709722497322
  },
  "financial": {
    "fcf": 406996000.0,
    "debt_ratio": 10.106511577051768,
    "gross_margin": 68.03519999999999
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.AMD
```json
{
  "code": "US.AMD",
  "current_price": 537.37,
  "today_change_pct": 4.856774898532623,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": 23.394,
    "pe_ttm": 202.781,
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "CPU/GPU/AI加速",
  "main_risk": "AI GPU竞争、利润率和估值分位偏高风险",
  "relation_to_existing_holdings": "非当前富途持仓；与AI/半导体主线相关",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 501.85725,
    "ma20_dist_pct": 7.076265212866795,
    "ma50": 411.0471,
    "ma50_dist_pct": 30.731976943761442,
    "ma200": 261.150225,
    "ma200_dist_pct": 105.77045261975174
  },
  "financial": {
    "fcf": 2566000000.0,
    "debt_ratio": 19.060294819316443,
    "gross_margin": 50.2803
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.ARM
```json
{
  "code": "US.ARM",
  "current_price": 439.46,
  "today_change_pct": 4.9131016042780695,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": 95.402,
    "pe_ttm": 517.011,
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "CPU IP/移动与边缘AI",
  "main_risk": "极高估值与授权收入增速不及预期风险",
  "relation_to_existing_holdings": "非当前富途持仓；与AI/半导体主线相关",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 362.29699999999997,
    "ma20_dist_pct": 21.29827185982771,
    "ma50": 264.5317,
    "ma50_dist_pct": 66.12753783383994,
    "ma200": 167.83342499999998,
    "ma200_dist_pct": 161.84295529927962
  },
  "financial": {
    "fcf": 979000000.0,
    "debt_ratio": 22.582453517705318,
    "gross_margin": 97.5407
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.KLAC
```json
{
  "code": "US.KLAC",
  "current_price": 259.56,
  "today_change_pct": 8.72533824823023,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": 25.888,
    "pe_ttm": 85.465,
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "半导体设备/检测量测",
  "main_risk": "半导体设备周期、对华限制与财务杠杆/负债风险",
  "relation_to_existing_holdings": "非当前富途持仓；与AI/半导体主线相关",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 214.8982,
    "ma20_dist_pct": 20.782770632792634,
    "ma50": 193.6026066887,
    "ma50_dist_pct": 34.06844279599761,
    "ma200": 144.11617407264998,
    "ma200_dist_pct": 80.10469794261536
  },
  "financial": {
    "fcf": null,
    "debt_ratio": 65.44587775576103,
    "gross_margin": 61.446400000000004
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```
### US.ALAB
```json
{
  "code": "US.ALAB",
  "current_price": 417.07,
  "today_change_pct": 11.313654318351652,
  "one_month_change_pct": "缺失",
  "three_month_change_pct": "缺失",
  "forward_pe_or_ps": {
    "forward_pe": "缺失",
    "ps_ttm": 71.386,
    "pe_ttm": 341.86,
    "note": "既有扫描只保存TTM/当前估值字段，未计算forward PE"
  },
  "market_cap": "缺失",
  "track": "AI互联芯片",
  "main_risk": "新股估值高、业绩兑现周期短、波动极大",
  "relation_to_existing_holdings": "非当前富途持仓；与AI/半导体主线相关",
  "existing_scan_source": {
    "mvp_scan_date": "2026-06-20 11:36:51 JST",
    "long_scan_date": "2026-06-21T08:45:28+09:00",
    "is_realtime": false,
    "note": "本字段来自既有扫描文件，非今日实时重算"
  },
  "ma_position": {
    "ma20": 347.573,
    "ma20_dist_pct": 19.99493631553659,
    "ma50": 258.0307,
    "ma50_dist_pct": 61.635805351843764,
    "ma200": 186.21939999999998,
    "ma200_dist_pct": 123.9669980678705
  },
  "financial": {
    "fcf": 67012000.0,
    "debt_ratio": 9.960553635303441,
    "gross_margin": 75.98939999999999
  },
  "score_if_available": "缺失",
  "data_gaps": [
    "1个月涨跌未算",
    "3个月涨跌未算",
    "forward PE未算",
    "市值字段未算"
  ]
}
```