# Decision Layer 明细

## US.GE / GE航天航空
{
  "code": "US.GE",
  "name": "GE航天航空",
  "current_status": {
    "current_price": 365.88,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量",
        "财报窗口未来30天内"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 365.88,
    "ideal_entry_range": {
      "lower": 307.732,
      "upper": 327.07,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 307.732,
      "upper": 317.401,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 307.732,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 307.732,
      "upper": 327.07,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "未来30天内",
    "product": [
      "航空发动机订单与交付节奏"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "航空航天供应链景气"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量",
      "财报窗口未来30天内"
    ]
  },
  "recommendation": {
    "level": "★★★★☆",
    "reason": "排第一：趋势、成交量、财报窗口和可解释性相对更完整；但估值空间不足，所以不是五星。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "GE排第一：相对HIMS/MU，GE同时具备短期趋势、成交量、财报窗口和较高流动性，解释链更完整；但仍因估值空间缺失而不转直接买入。"
}

## US.HIMS / Hims & Hers Health
{
  "code": "US.HIMS",
  "name": "Hims & Hers Health",
  "current_status": {
    "current_price": 32.7,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "放量突破近期高点",
        "成交量>20日均量1.5倍",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 32.7,
    "ideal_entry_range": {
      "lower": 26.644,
      "upper": 27.697,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 26.644,
      "upper": 27.1705,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 26.644,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 26.644,
      "upper": 27.697,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "AI医疗/线上医疗产品增长验证"
    ],
    "policy": [
      "医疗监管与处方相关政策"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "放量突破近期高点",
      "成交量>20日均量1.5倍",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "排第二：短线动量强，但财务/估值数据缺口和波动风险高。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "HIMS排第二：短线动量和放量突破强，但财务红旗、估值模型缺失和波动风险高于GE。"
}

## US.MU / 美光科技
{
  "code": "US.MU",
  "name": "美光科技",
  "current_status": {
    "current_price": 1048.51,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "放量突破近期高点",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量",
        "财报窗口未来7天内"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 1048.51,
    "ideal_entry_range": {
      "lower": 732.7992,
      "upper": 965.5775,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 732.7992,
      "upper": 849.1884,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 732.7992,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 732.7992,
      "upper": 965.5775,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "未来7天内",
    "product": [
      "存储/HBM需求与AI服务器链验证"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "AI硬件链与存储周期"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "放量突破近期高点",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量",
      "财报窗口未来7天内"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "不是第一：中期分数高，但当前价格明显高于技术参考区间且估值分位偏高，财报前不适合直接优先。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "MU不是第一：中期得分高且有财报催化，但当前价高于20MA/50MA技术参考区间，PE/PS分位偏高，财报前追高风险更大。"
}

## US.IMMR / 浸入科技
{
  "code": "US.IMMR",
  "name": "浸入科技",
  "current_status": {
    "current_price": 6.5,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 6.5,
    "ideal_entry_range": {
      "lower": 6.3082,
      "upper": 6.504,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 6.3082,
      "upper": 6.4061,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 6.3082,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 6.3082,
      "upper": 6.504,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "触觉反馈/AI眼镜或终端设备采用"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.MEI / Methode Electronics
{
  "code": "US.MEI",
  "name": "Methode Electronics",
  "current_status": {
    "current_price": 13.09,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "放量突破近期高点",
        "成交量>20日均量1.5倍",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量",
        "财报窗口未来7天内"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 13.09,
    "ideal_entry_range": {
      "lower": 9.8964,
      "upper": 11.761,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 9.8964,
      "upper": 10.8287,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 9.8964,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 9.8964,
      "upper": 11.761,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "未来7天内",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "工业自动化/电子零部件需求"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "放量突破近期高点",
      "成交量>20日均量1.5倍",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量",
      "财报窗口未来7天内"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "分数较高，但数据源stale且估值空间不可得，保持三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.FTV / Fortive
{
  "code": "US.FTV",
  "name": "Fortive",
  "current_status": {
    "current_price": 60.39,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 60.39,
    "ideal_entry_range": {
      "lower": 60.179,
      "upper": 60.275,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 60.179,
      "upper": 60.227,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 60.179,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 60.179,
      "upper": 60.275,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "工业自动化/电子零部件需求"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.AAPL / 苹果
{
  "code": "US.AAPL",
  "name": "苹果",
  "current_status": {
    "current_price": 293.08,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 293.08,
    "ideal_entry_range": {
      "lower": 288.6298,
      "upper": 303.3975,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 288.6298,
      "upper": 296.0136,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 288.6298,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 288.6298,
      "upper": 303.3975,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.CVLT / 康沃系统
{
  "code": "US.CVLT",
  "name": "康沃系统",
  "current_status": {
    "current_price": 130.76,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 130.76,
    "ideal_entry_range": {
      "lower": 106.4399,
      "upper": 119.853,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 106.4399,
      "upper": 113.1464,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 106.4399,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 106.4399,
      "upper": 119.853,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.EMR / 艾默生电气
{
  "code": "US.EMR",
  "name": "艾默生电气",
  "current_status": {
    "current_price": 141.44,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 141.44,
    "ideal_entry_range": {
      "lower": 140.5753,
      "upper": 142.0555,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 140.5753,
      "upper": 141.3154,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 140.5753,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 140.5753,
      "upper": 142.0555,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ETN / 伊顿
{
  "code": "US.ETN",
  "name": "伊顿",
  "current_status": {
    "current_price": 404.59,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 404.59,
    "ideal_entry_range": {
      "lower": 402.4945,
      "upper": 404.6264,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 402.4945,
      "upper": 403.5605,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 402.4945,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 402.4945,
      "upper": 404.6264,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.CAH / 卡地纳健康
{
  "code": "US.CAH",
  "name": "卡地纳健康",
  "current_status": {
    "current_price": 233.01,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "成交量>20日均量1.5倍",
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 233.01,
    "ideal_entry_range": {
      "lower": 203.7286,
      "upper": 208.6055,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 203.7286,
      "upper": 206.1671,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 203.7286,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 203.7286,
      "upper": 208.6055,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍",
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.INDI / indie Semiconductor
{
  "code": "US.INDI",
  "name": "indie Semiconductor",
  "current_status": {
    "current_price": 3.57,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 3.57,
    "ideal_entry_range": {
      "lower": 4.1136,
      "upper": 4.5005,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 4.1136,
      "upper": 4.3071,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 4.1136,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 4.1136,
      "upper": 4.5005,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "技术条件较好，但缺估值空间和执行确认，仅三星观察。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ASML / 阿斯麦
{
  "code": "US.ASML",
  "name": "阿斯麦",
  "current_status": {
    "current_price": 1762.77,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "价格站上20/50/200MA且均线多头排列",
        "价格站上三均线且放量",
        "财报窗口未来30天内"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 1762.77,
    "ideal_entry_range": {
      "lower": 1579.2284,
      "upper": 1732.5465,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 1579.2284,
      "upper": 1655.8874,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 1579.2284,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 1579.2284,
      "upper": 1732.5465,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "未来30天内",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "价格站上20/50/200MA且均线多头排列",
      "价格站上三均线且放量",
      "财报窗口未来30天内"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.WRBY / Warby Parker
{
  "code": "US.WRBY",
  "name": "Warby Parker",
  "current_status": {
    "current_price": 26.85,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "positive_trend",
      "evidence": [
        "价格站上20/50/200MA且均线多头排列"
      ],
      "price_vs_reference_range": "above_upper_reference"
    }
  },
  "cost_reference": {
    "current_price": 26.85,
    "ideal_entry_range": {
      "lower": 24.6602,
      "upper": 24.9455,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 24.6602,
      "upper": 24.8028,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 24.6602,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 24.6602,
      "upper": 24.9455,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "当前价高于技术参考区间上沿，追高风险大于等待回落。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "快照缺口:获取市场快照频率太高，请求失败，每30秒最多60次。",
      "未来财报日期缺失",
      "历史估值分位缺失"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "价格站上20/50/200MA且均线多头排列"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.MVIS / 维视图像
{
  "code": "US.MVIS",
  "name": "维视图像",
  "current_status": {
    "current_price": 0.3113,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 0.3113,
    "ideal_entry_range": {
      "lower": 0.4678,
      "upper": 0.5739,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 0.4678,
      "upper": 0.5209,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 0.4678,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 0.4678,
      "upper": 0.5739,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.DQ / 大全新能源
{
  "code": "US.DQ",
  "name": "大全新能源",
  "current_status": {
    "current_price": 13.38,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 13.38,
    "ideal_entry_range": {
      "lower": 16.076,
      "upper": 18.5302,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 16.076,
      "upper": 17.3031,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 16.076,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 16.076,
      "upper": 18.5302,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.NNOX / Nano X Imaging
{
  "code": "US.NNOX",
  "name": "Nano X Imaging",
  "current_status": {
    "current_price": 1.57,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "财报窗口未来7天内"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 1.57,
    "ideal_entry_range": {
      "lower": 1.841,
      "upper": 1.916,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 1.841,
      "upper": 1.8785,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 1.841,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 1.841,
      "upper": 1.916,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "未来7天内",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "财报窗口未来7天内"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ADBE / Adobe
{
  "code": "US.ADBE",
  "name": "Adobe",
  "current_status": {
    "current_price": 196.57,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 196.57,
    "ideal_entry_range": {
      "lower": 235.7335,
      "upper": 241.6615,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 235.7335,
      "upper": 238.6975,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 235.7335,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 235.7335,
      "upper": 241.6615,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ADSK / 欧特克
{
  "code": "US.ADSK",
  "name": "欧特克",
  "current_status": {
    "current_price": 192.61,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 192.61,
    "ideal_entry_range": {
      "lower": 223.398,
      "upper": 232.5194,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 223.398,
      "upper": 227.9587,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 223.398,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 223.398,
      "upper": 232.5194,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.OLED / Universal Display
{
  "code": "US.OLED",
  "name": "Universal Display",
  "current_status": {
    "current_price": 87.56,
    "valuation_status": {
      "status": "unknown",
      "explanation": "缺少可复核的PE/PS历史分位或目标估值模型；不能判断便宜或贵。"
    },
    "trend_status": {
      "status": "below_reference_range",
      "evidence": [
        "成交量>20日均量1.5倍"
      ],
      "price_vs_reference_range": "inside_or_below_reference"
    }
  },
  "cost_reference": {
    "current_price": 87.56,
    "ideal_entry_range": {
      "lower": 90.4162,
      "upper": 92.6584,
      "basis": "沿用数据层20MA/50MA技术参考区间；不是估值公允价，不是下单指令。"
    },
    "ideal_add_range": {
      "lower": 90.4162,
      "upper": 91.5373,
      "basis": "仅当趋势未破且价格回到参考区间下半段，才作为加仓观察区；不是下单指令。"
    },
    "abandon_price": {
      "value": 90.4162,
      "rule": "若价格跌破技术参考区间下沿且成交量/趋势同步失效，放弃短期动作；不是自动卖出或下单指令。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": 90.4162,
      "upper": 92.6584,
      "currency": "original_market_currency",
      "method": "20MA/50MA 技术参考区间；不是估值公允价，不是下单指令",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。 同时存在财报日期或事件数据缺口。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [
      "未来财报日期缺失",
      "历史估值分位缺失",
      "ROE/毛利率/营收增速缺失；未计算护城河"
    ],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报窗口或业绩验证",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": [
      "成交量>20日均量1.5倍"
    ]
  },
  "recommendation": {
    "level": "★★☆☆☆",
    "reason": "数据缺口较多，暂不提高推荐等级。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.DOCU / DocuSign
{
  "code": "US.DOCU",
  "name": "DocuSign",
  "current_status": {
    "current_price": 44.24,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 44.67713787085515,
      "ps_percentile": 0.1593625,
      "explanation": "可用估值分位最低为 0.16%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 44.24,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ISRG / 直觉外科公司
{
  "code": "US.ISRG",
  "name": "直觉外科公司",
  "current_status": {
    "current_price": 401.83,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 10.358565737051793,
      "ps_percentile": 10.1195219,
      "explanation": "可用估值分位最低为 10.12%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 401.83,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.CRDO / Credo Technology
{
  "code": "US.CRDO",
  "name": "Credo Technology",
  "current_status": {
    "current_price": 268.99,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 5.303030303030303,
      "ps_percentile": 84.6642468,
      "explanation": "可用估值分位最低为 5.30%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 268.99,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.ASYS / Amtech Systems
{
  "code": "US.ASYS",
  "name": "Amtech Systems",
  "current_status": {
    "current_price": 22.04,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 0.19193857965451055,
      "ps_percentile": 99.7609561,
      "explanation": "可用估值分位最低为 0.19%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 22.04,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.MSFT / 微软
{
  "code": "US.MSFT",
  "name": "微软",
  "current_status": {
    "current_price": 365.46,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 11.952191235059761,
      "ps_percentile": 3.7450199,
      "explanation": "可用估值分位最低为 3.75%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 365.46,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## US.META / Meta Platforms
{
  "code": "US.META",
  "name": "Meta Platforms",
  "current_status": {
    "current_price": 577.22,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 26.374501992031874,
      "ps_percentile": 36.812749,
      "explanation": "可用估值分位最低为 26.37%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 577.22,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## JP.6723 / 瑞萨电子
{
  "code": "JP.6723",
  "name": "瑞萨电子",
  "current_status": {
    "current_price": 4734.0,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 0.2457002,
      "ps_percentile": 99.8361998,
      "explanation": "可用估值分位最低为 0.25%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 4734.0,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## JP.2158 / Fronteo
{
  "code": "JP.2158",
  "name": "Fronteo",
  "current_status": {
    "current_price": 580.0,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 57.9033579,
      "ps_percentile": 3.9312039,
      "explanation": "可用估值分位最低为 3.93%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 580.0,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## JP.3993 / PKSHA Technology
{
  "code": "JP.3993",
  "name": "PKSHA Technology",
  "current_status": {
    "current_price": 2744.0,
    "valuation_status": {
      "status": "attractive_or_discounted_by_available_percentile",
      "pe_percentile": 13.8411138,
      "ps_percentile": 0.7371007,
      "explanation": "可用估值分位最低为 0.74%，至少一项低于30%。"
    },
    "trend_status": {
      "status": "unknown_or_needs_refresh",
      "evidence": "该字段未算或候选来自长期估值池。",
      "price_vs_reference_range": "reference_unavailable"
    }
  },
  "cost_reference": {
    "current_price": 2744.0,
    "ideal_entry_range": {
      "lower": null,
      "upper": null,
      "basis": "缺少可靠20MA/50MA参考区间或候选来自长期估值池；等待行情数据刷新。"
    },
    "ideal_add_range": {
      "lower": null,
      "upper": null,
      "basis": "无法计算加仓区间；等待行情数据接入后确认。"
    },
    "abandon_price": {
      "value": null,
      "rule": "放弃价格无法可靠计算；等待行情数据接入后确认。"
    },
    "decision_reference_only": true,
    "not_trade_instruction": true,
    "raw_reference": {
      "lower": null,
      "upper": null,
      "currency": null,
      "method": "待估值模型确认；当前无可靠成本区间",
      "is_trade_instruction": false
    }
  },
  "space_judgement": {
    "reasonable_value_range": {
      "lower": null,
      "upper": null,
      "status": "unavailable",
      "reason": "当前Product_Data_Layer没有DCF、PEG、目标PE/PS或同行估值模型输出；不得编造合理价值区间。"
    },
    "distance_to_reasonable_value_pct": {
      "value": null,
      "reason": "合理价值区间不可得，因此无法计算当前距离合理价值。"
    },
    "expected_space": {
      "value": null,
      "reason": "预期空间需要目标估值模型或研报确认；当前仅有技术/扫描候选证据。"
    },
    "reliability": "insufficient_valuation_model"
  },
  "risk_judgement": {
    "maximum_risk": "候选数据源过期、估值空间缺失，且账户现金/执行字段未进入动作确认。",
    "invalidation_conditions": [
      "跌回20MA/50MA参考区间下方且无法快速收复。",
      "放量突破逻辑消失，成交量回落或转为放量下跌。",
      "财报/基本面验证与候选逻辑相反。"
    ],
    "why_not_buy_today": [
      "候选源存在stale或数据缺口，需要刷新确认。",
      "没有可靠合理价值区间，不能把技术区间当成估值安全边际。",
      "数据层缺少账户现金、挂单、执行约束的完整确认；不得直接转交易动作。"
    ],
    "data_gaps": [],
    "stale_source": true
  },
  "catalysts": {
    "earnings": "接口未返回未来财报日期",
    "product": [
      "暂无明确产品催化；需专题研报确认"
    ],
    "policy": [
      "暂无明确政策催化；仅保留风险观察"
    ],
    "industry_events": [
      "所属主题景气度与资金流"
    ],
    "true_catalysts": [
      "财报日期待补",
      "价格/量能继续验证而非单日脉冲"
    ],
    "source_evidence": []
  },
  "recommendation": {
    "level": "★★★☆☆",
    "reason": "估值分位有吸引力，但长期候选缺护城河复核和今日动作条件。",
    "not_trade_instruction": true
  },
  "why_ranked_here": "按当前候选层级、技术条件、数据完整度和风险缺口排序；不是交易优先级。"
}

## Reverse PK
[
  {
    "code": "US.NVDA",
    "evaluated": true,
    "current_price": 199.0,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.AVGO",
    "evaluated": true,
    "current_price": 382.07,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.ARM",
    "evaluated": true,
    "current_price": 359.08,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.AMD",
    "evaluated": true,
    "current_price": 519.74,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.KLAC",
    "evaluated": true,
    "current_price": 240.48,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.CRDO",
    "evaluated": true,
    "current_price": 268.99,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  },
  {
    "code": "US.ALAB",
    "evaluated": true,
    "current_price": 399.92,
    "why_not_priority_today": "已评估，但未进入今天短期/中期Top3；当前数据层显示其不是今日最优新增机会。",
    "comparison_with_current_opportunities": {
      "current_priority_examples": [
        "US.GE",
        "US.HIMS",
        "US.MU"
      ],
      "better_than_current_opportunity": null,
      "reason": "需要最新估值空间与全市场刷新；当前数据层只给同源扫描/过滤器证据。"
    },
    "raw_evidence": {
      "scan_row_available": true,
      "filter_score_available": false,
      "filter_scores": []
    }
  }
]