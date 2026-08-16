#!/usr/bin/env python3
"""Place already-approved v0.4 content in the required three-layer reading structure."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))


FIRST_LAYER_INSERT = """
<section id="first-screen-closure" class="layer-closure">
<h3>＋40%／＋100%目标差距</h3>
<div class="grid">
<div class="panel"><b>＋40%目标</b><p>缺少经确认的统一年初净值，当前不能诚实计算精确完成度。要接近目标，需要核心持仓盈利继续兑现，并由更好风险收益比的新机会补充贡献；今天不能为了补差距追高。</p></div>
<div class="panel"><b>＋100%目标</b><p>需要多个高弹性机会同时兑现，且组合回撤受控。当前AI同一驱动暴露已高，主要候选估值也不低，因此今天不把高目标转换成高风险订单。</p></div>
</div>
<h3>重点机会及为什么暂不买</h3>
<p>ETN、CEG、MUFG、TSM、VRT、SMFG、瑞穗和ASML属于第一层观察名单，但都只是等待触发条件。当前价格下，估值、安全边际或下一次财报确认尚不足，所以当前可执行新机会仍为0。</p>
<h3>数据缺口怎样影响今天</h3>
<p>SBI、IBKR和bitFlyer是董事长确认未交易后的最后已知状态，不能与富途拼成同日净值；SNDK券商收益率口径仍不明；富途其他净资产只有汇总值。结果是：可以做风险观察和研究排序，但不能据此计算精确年度完成度、形成全账户精确仓位或生成交易动作。</p>
</section>
"""


SECOND_LAYER_INSERT = """
<section id="second-layer-business-closure" class="layer-closure">
<h3>三种年度目标情景</h3>
<table><thead><tr><th>情景</th><th>成立条件</th><th>对目标的含义</th><th>今天怎么办</th></tr></thead><tbody>
<tr><td>保守</td><td>AI资本开支放缓、估值收缩，日本利率或汇率不利</td><td>先保护回撤，＋40%和＋100%都难以实现</td><td>保留现金，执行失效条件和替代预案，不机械减仓</td></tr>
<tr><td>中性</td><td>核心盈利继续增长，AI需求消化估值，非AI资产提供分散</td><td>＋40%仍需核心持仓和新机会共同贡献</td><td>持有核心，等待第一层候选达到更有利条件</td></tr>
<tr><td>激进</td><td>AI、存储和电力链同时兑现，高弹性资产上涨且回撤可控</td><td>＋100%需要多项高弹性机会共同成功，不能靠单一持仓</td><td>不预支乐观情景；只有证据和价格同时满足才重新评估</td></tr>
</tbody></table>
<h3>保留、减少和替代关系</h3>
<ul>
<li>微软、NVIDIA等核心持仓以持有为主，但不追高；新增AI仓位必须先与现有广义AI暴露比较。</li>
<li>加密相关保留顺序为COIN、CRCL、MSTR；MSTR不补仓，是第一顺位替换或压缩对象，但不是自动卖单。</li>
<li>软银是广义AI代理敞口；风险恶化或出现更高胜率替代机会时，才进入优先调整讨论。</li>
<li>SNDK持有但不增加，券商市值进入风险，未闭合的收益率不进入估值或动作。</li>
</ul>
<h3>候选机会比较</h3>
<p><b>第一层：</b>ETN、CEG、MUFG、TSM、VRT、SMFG、瑞穗、ASML，等待估值、财报或事件触发。<b>第二层：</b>CRDO、MU、WDC、XOM、CVX，继续研究但当前吸引力不足。<b>第三层：</b>SNDK、NVDA、AVGO、PLTR、ON、COHR、LITE、NRG，当前不新增。PLTR和ON通过基础扫描不等于可以买入。</p>
<h3>PDCA验证结果</h3>
<p>现有记录包含5个独立预测系列和57个连续跟踪点。29个跟踪点已判定，其中28个一致、1个不一致，另有28个待验证。28/29＝96.552%只能称为“已判定跟踪点的一致率”；5个独立系列样本过少，不能称为独立预测准确率、投资胜率、交易胜率或系统预测能力。</p>
</section>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", required=True)
    args = parser.parse_args()
    output_dir = Path(args.dir).resolve()
    html_path = next(output_dir.glob("★*v0.4.html"))
    product = html_path.read_text(encoding="utf-8")
    if 'id="first-screen-closure"' in product or 'id="second-layer-business-closure"' in product:
        raise SystemExit("Layer closure sections already exist")
    first_anchor = "<h3>全账户覆盖状态</h3>"
    second_anchor = "<h3>外部观点如何使用</h3>"
    if first_anchor not in product or second_anchor not in product:
        raise SystemExit("Required insertion anchor is missing")
    product = product.replace(first_anchor, FIRST_LAYER_INSERT + first_anchor, 1)
    product = product.replace(second_anchor, SECOND_LAYER_INSERT + second_anchor, 1)
    product = product.replace(
        "未调用交易接口，未生成或执行订单。",
        "只调用OpenD账户与持仓只读查询；未调用交易解锁、下单、改单或撤单功能，未生成或执行订单。",
    )
    html_path.write_text(product, encoding="utf-8")

    log_path = output_dir / "15_完整施工日志和修改前后清单_20260817.json"
    log = json.loads(log_path.read_text(encoding="utf-8-sig"))
    log["layer_structure_closure"] = {
        "completed_at": datetime.now(JST).isoformat(timespec="seconds"),
        "first_screen": ["目标差距", "重点机会及暂不买原因", "数据缺口对今日动作的影响"],
        "second_layer": ["三种年度情景", "保留减少替代关系", "候选比较", "PDCA验证结果"],
        "new_investment_judgment_added": False,
    }
    log["boundaries"] = {
        "release_registered": False,
        "daily_overwritten": False,
        "trade_functions_called": False,
        "orders_generated": False,
        "current_rules_modified": False,
        "opend_read_only_queries_used": True,
    }
    log.pop("prohibitions", None)
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    log_html_path = output_dir / "15_完整施工日志和修改前后清单_20260817.html"
    log_html = log_html_path.read_text(encoding="utf-8")
    log_html = log_html.replace(
        "未Release、未覆盖正式日报、未调用交易接口、未生成订单。",
        "只调用OpenD账户与持仓只读查询；未调用交易解锁、下单、改单或撤单功能。未Release、未覆盖正式日报、未生成订单。",
    )
    log_html = log_html.replace(
        "</ul>",
        "<li>按开工令补齐第一屏目标差距、机会暂不买原因和数据缺口影响。</li>"
        "<li>把三情景、替代关系、候选比较和PDCA摘要置入第二层。</li></ul>",
        1,
    )
    log_html_path.write_text(log_html, encoding="utf-8")
    print(json.dumps({"status": "UPDATED", "html": str(html_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
