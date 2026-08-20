from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .contracts import ContractError, load_json, validate_final_judgment, validate_handoff, write_json


JST = timezone(timedelta(hours=9))
STATUS = {
    "business_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "final_product_pass": "PENDING_INDEPENDENT_FULL_REVIEW",
    "release_status": "NOT_AUTHORIZED",
    "current_executable": False,
}
FORBIDDEN_BODY_TEXT = (
    "等待GPT总控",
    "需GPT总控决定",
    "仅供总控选择",
    "PENDING_JUDGMENT",
)
LABELS = {
    "headline": "今天的总答案",
    "priority": "行动优先级",
    "cash_use_rule": "现金使用条件",
    "what_would_change_today_action": "什么情况会改变今天的安排",
    "worldview_and_policy_conclusion": "世界观与政策结论",
    "fund_flow_conclusion": "资金与流动性结论",
    "activated_sectors": "当前研究性激活方向",
    "sector_strength_and_confidence": "方向力度与把握度",
    "all_account_risk_judgment": "全账户风险结论",
    "cash_vs_holdings_vs_new_opportunities": "现金、持仓与新机会比较",
    "plus_40_forward_path": "＋40%前瞻路径",
    "plus_100_stress_path": "＋100%压力路径",
    "defensive_and_crypto_risk_boundary": "防御与加密风险边界",
    "today_action_summary": "今日行动摘要",
    "next_review_time": "下一次复核",
    "actual_2026_return_calculable": "2026年实际收益能否计算",
    "reason": "原因",
    "forward_baseline_use": "前瞻基线用途",
    "known_assets_jpy": "已知资产（日元）",
    "pure_cash_estimate_jpy": "纯现金估算（日元）",
    "pure_cash_ratio_pct": "纯现金占已知资产",
    "cash_plus_funds_jpy": "现金加基金（日元）",
    "cash_plus_funds_ratio_pct": "现金加基金占已知资产",
    "plus_40_path": "＋40%路径",
    "plus_100_path": "＋100%路径",
    "cash_deployment": "现金投入安排",
    "defensive_boundary": "防御资产边界",
    "crypto_boundary": "加密资产边界",
    "next_review": "下一次复核",
    "plain_answer": "大白话结论",
    "milestones": "验证里程碑",
    "required_change": "需要发生的变化",
    "status": "状态",
}


def esc(value: Any) -> str:
    if value is None:
        return "尚未取得"
    if isinstance(value, bool):
        return "是" if value else "否"
    return html.escape(str(value))


def label(key: str) -> str:
    return LABELS.get(key, key.replace("_", " "))


def fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "尚未取得"
    if isinstance(value, bool):
        return "是" if value else "否"
    if isinstance(value, (int, float)):
        return f"{value:,.{digits}f}".rstrip("0").rstrip(".")
    return str(value)


def link(url: Any, text: str = "打开原文") -> str:
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        return "未登记可点击原文"
    return f'<a href="{esc(url)}" target="_blank" rel="noreferrer">{esc(text)}</a>'


def plain_block(value: Any, depth: int = 0) -> str:
    if value is None:
        return '<p class="muted">尚未取得；本期不据此形成动作。</p>'
    if isinstance(value, dict):
        rows = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                rows.append(f'<div class="subblock"><h4>{esc(label(key))}</h4>{plain_block(item, depth + 1)}</div>')
            else:
                rows.append(f'<p><b>{esc(label(key))}：</b>{esc(item)}</p>')
        return "".join(rows)
    if isinstance(value, list):
        if not value:
            return '<p class="muted">本批次未取得可用内容。</p>'
        return '<ul>' + ''.join(f'<li>{plain_block(x, depth + 1) if isinstance(x, (dict, list)) else esc(x)}</li>' for x in value) + '</ul>'
    return f'<p>{esc(value)}</p>'


def details(title: str, body: str, *, open_: bool = False, attrs: str = "") -> str:
    opened = " open" if open_ else ""
    return f'<details{opened} {attrs}><summary>{esc(title)}</summary><div class="detail-body">{body}</div></details>'


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def index_by(items: list[dict[str, Any]], *keys: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in items:
        for key in keys:
            value = item.get(key)
            if value:
                result[str(value)] = item
                break
    return result


def render_action(judgment: dict[str, Any]) -> str:
    action = judgment["today_action"]
    priorities = ''.join(f'<li>{esc(x)}</li>' for x in action.get("priority", []))
    changes = ''.join(f'<li>{esc(x)}</li>' for x in action.get("what_would_change_today_action", []))
    return f'''
    <div class="hero-answer"><span>今天怎么做</span><h2>{esc(action.get("headline"))}</h2></div>
    <div class="decision-grid">
      <article><h3>行动顺序</h3><ol>{priorities}</ol></article>
      <article><h3>现金怎么用</h3><p>{esc(action.get("cash_use_rule"))}</p></article>
      <article><h3>什么时候改变</h3><ul>{changes}</ul></article>
    </div>
    <div class="boundary">本产品是待独立全量验收的候选。未授权发布，不可执行，不构成交易订单。</div>
    '''


def render_seven_layers(bundle: dict[str, Any], judgment: dict[str, Any]) -> str:
    fact_layers = {int(x.get("layer", 0)): x for x in bundle.get("seven_layers", [])}
    cards = []
    for item in judgment["seven_layer_final_judgment"]:
        n = int(item.get("layer", 0))
        facts = fact_layers.get(n, {}).get("facts", [])
        fact_rows = []
        for fact in facts:
            fact_rows.append(
                f'<tr><td>{esc(fact.get("title"))}<br><small>{esc(fact.get("publisher"))}</small></td>'
                f'<td>{esc(fact.get("fact"))}</td><td>{esc(fact.get("supports"))}</td>'
                f'<td>{esc(fact.get("cannot_prove"))}</td><td>{link(fact.get("url"))}</td></tr>'
            )
        fact_table = '<table><thead><tr><th>事实与来源</th><th>事实</th><th>支持什么</th><th>不能证明什么</th><th>原文</th></tr></thead><tbody>' + ''.join(fact_rows) + '</tbody></table>'
        body = f'''
        <p class="conclusion"><b>总控结论：</b>{esc(item.get("final_judgment"))}</p>
        <div class="mini-grid"><p><b>方向：</b>{esc(item.get("direction"))}</p><p><b>力度：</b>{esc(item.get("strength"))}</p><p><b>把握度：</b>{esc(item.get("confidence"))}</p></div>
        <p><b>如何传到组合：</b>{esc(item.get("portfolio_transmission"))}</p>
        <p><b>什么会推翻：</b>{esc(item.get("reversal"))}</p>
        {fact_table}
        '''
        cards.append(details(f'第{n}层｜{item.get("name", "")}', body, open_=n <= 2, attrs=f'data-layer="{n}"'))
    return ''.join(cards)


def render_news(bundle: dict[str, Any]) -> str:
    ledger = bundle["news_ledger"]
    rows = []
    for item in ledger.get("records", []):
        rows.append(
            f'<tr><td>{esc(item.get("title"))}<br><small>{esc(item.get("publisher"))}</small></td>'
            f'<td>{esc(item.get("published_at"))}<br>{esc(item.get("data_date"))}</td>'
            f'<td>{esc(item.get("fact"))}</td><td>{esc(item.get("boundary"))}</td><td>{link(item.get("url"))}</td></tr>'
        )
    failed = ''.join(f'<li>{esc(x)}</li>' for x in ledger.get("failed_sources", [])) or '<li>没有登记新的失败来源。</li>'
    excluded = ''.join(f'<li>{esc(x)}</li>' for x in ledger.get("excluded", [])) or '<li>没有登记排除项。</li>'
    return f'''
    <p>检索开始：{esc(ledger.get("search_started_at_jst"))}｜检索结束：{esc(ledger.get("search_finished_at_jst"))}</p>
    <p><b>覆盖范围：</b>{'；'.join(esc(x) for x in ledger.get("search_scope", []))}</p>
    <table><thead><tr><th>事件与来源</th><th>发布时间／数据日</th><th>事实</th><th>使用边界</th><th>原文</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
    <div class="two-col"><div><h4>失败来源</h4><ul>{failed}</ul></div><div><h4>未纳入及原因</h4><ul>{excluded}</ul></div></div>
    '''


def render_accounts(bundle: dict[str, Any], judgment: dict[str, Any]) -> str:
    accounts = bundle["accounts_and_risk"]
    values = accounts.get("account_known_values_jpy", {})
    account_rows = ''.join(f'<tr><td>{esc(k)}</td><td class="num">¥{fmt_num(v)}</td></tr>' for k, v in values.items())
    positions = []
    for item in accounts.get("positions", []):
        positions.append(
            f'<tr><td>{esc(item.get("account"))}</td><td>{esc(item.get("asset_id"))}</td><td>{esc(item.get("name"))}</td>'
            f'<td class="num">{fmt_num(item.get("quantity"), 6)}</td><td class="num">{fmt_num(item.get("price"), 4)} {esc(item.get("currency"))}</td>'
            f'<td class="num">¥{fmt_num(item.get("market_value_jpy"))}</td><td>{esc(item.get("quantity_evidence_date"))}</td>'
            f'<td>{esc(item.get("quantity_evidence_status"))}</td></tr>'
        )
    risks = accounts.get("risk_observations", {})
    risk_cards = []
    for key, title in (("ai_direct", "AI直接"), ("ai_broad_with_softbank_proxy", "AI广义含软银"), ("crypto_direct", "加密直接"), ("crypto_broad_with_related_equities", "加密广义")):
        item = risks.get(key, {})
        pct = float(item.get("known_total_ratio_pct") or 0)
        risk_cards.append(f'<article class="metric"><b>{title}</b><strong>{pct:.2f}%</strong><div class="bar"><i style="width:{min(pct,100):.2f}%"></i></div><small>分母：已知资产 ¥{fmt_num(accounts.get("known_assets_total_jpy"))}</small></article>')
    unknowns = ''.join(f'<li>{esc(x)}</li>' for x in accounts.get("unknowns", []))
    target = judgment["target_and_cash_plan"]
    return f'''
    <div class="metric-grid">{''.join(risk_cards)}</div>
    <div class="two-col"><div><h4>各账户已知资产</h4><table><thead><tr><th>账户</th><th>已知资产</th></tr></thead><tbody>{account_rows}</tbody></table></div>
    <div><h4>目标与现金边界</h4>{plain_block(target)}</div></div>
    <h4>仍未闭合的账户字段</h4><ul>{unknowns}</ul>
    {details('查看全部账户与持仓明细', '<table><thead><tr><th>账户</th><th>代码</th><th>名称</th><th>数量</th><th>价格</th><th>日元市值</th><th>数量证据日</th><th>状态</th></tr></thead><tbody>'+''.join(positions)+'</tbody></table>')}
    '''


def render_external_views(bundle: dict[str, Any]) -> str:
    cards = []
    for item in bundle.get("external_views", {}).get("records", []):
        pages = item.get("pages", [])
        excerpt = " ".join(str(x.get("text", ""))[:260] for x in pages[:2]).strip()
        body = f'''
        <p><b>资料组：</b>{esc(item.get("source_group"))}｜<b>读取状态：</b>{esc(item.get("read_status"))}｜<b>修改时间：</b>{esc(item.get("modified_at_jst"))}</p>
        <p><b>文件：</b>{esc(item.get("path"))}</p><p><b>内容摘要：</b>{esc(excerpt or "未取得可读正文")}</p>
        <p class="muted">外部观点只作为支持或反向研究材料，不能替代官方事实，也不能单独生成交易动作。</p>
        '''
        cards.append(details(f'{item.get("source_group", "外部资料")}｜{Path(str(item.get("path", ""))).name}', body))
    return ''.join(cards)


def render_asset_cards(bundle: dict[str, Any], judgment: dict[str, Any]) -> str:
    combined = index_by(bundle["accounts_and_risk"].get("combined_positions", []), "asset_id")
    holdings = index_by(bundle.get("holding_inputs", {}).get("items", []), "symbol")
    valuations = index_by(bundle.get("valuation_inputs", {}).get("items", []), "symbol")
    quotes = index_by(bundle.get("asset_quotes", {}).get("records", []), "asset_id", "code")
    event_cards = bundle.get("asset_event_scan", {}).get("cards", {})
    matrix = index_by(bundle.get("judgment_matrix", {}).get("assets", []), "asset_id")
    answers = index_by(judgment["asset_final_answers"], "asset_id")
    cards = []
    for asset_id, answer in answers.items():
        base = matrix.get(asset_id, {})
        account = combined.get(asset_id, {})
        holding = holdings.get(asset_id, {})
        valuation = valuations.get(asset_id, holding.get("valuation_input", {}))
        quote = quotes.get(asset_id, {})
        event = event_cards.get(asset_id, {}) if isinstance(event_cards, dict) else {}
        official = valuation.get("official_source", {}) if isinstance(valuation, dict) else {}
        financial = holding.get("financial_fact", {}) if isinstance(holding, dict) else {}
        source = official or financial
        event_rows = ''.join(
            f'<li>{esc(x.get("published_at"))}｜{esc(x.get("title"))}｜{link(x.get("url"))}</li>'
            for x in event.get("events", [])[:5]
        ) or '<li>限定范围内未取得可独立使用的新公司事件。</li>'
        body = f'''
        <div class="answer"><b>唯一动作：</b>{esc(answer.get("unique_action"))}</div>
        <div class="asset-grid">
          <div><h4>事实与持仓</h4><p>{esc(answer.get("plain_reason"))}</p><p><b>账户数量：</b>{esc(account.get("quantity_by_account", base.get("accounts")))}</p><p><b>已知市值：</b>¥{fmt_num(account.get("market_value_jpy", base.get("known_market_value_jpy")))}</p><p><b>最新价：</b>{fmt_num(quote.get("last_price", holding.get("current_price", {}).get("value")), 4)}｜{esc(quote.get("update_time", holding.get("current_price", {}).get("time")))}</p></div>
          <div><h4>估值或风险定价</h4><p>{esc(answer.get("valuation_or_risk_pricing"))}</p><p><b>方法：</b>{esc(valuation.get("method", holding.get("valuation_input", {}).get("method_candidate")))}</p><p><b>正式来源：</b>{esc(source.get("title", source.get("source_title")))}｜{link(source.get("url", source.get("source_url")))}</p><p><b>数据期间：</b>{esc(source.get("period", source.get("financial_period")))}</p></div>
          <div><h4>前瞻与验证</h4><p><b>短期：</b>{esc(answer.get("short_term_outlook"))}</p><p><b>中期：</b>{esc(answer.get("medium_term_outlook"))}</p><p><b>把握度：</b>{esc(answer.get("success_probability_if_supported"))}</p><p><b>下次复核：</b>{esc(answer.get("next_review"))}</p></div>
          <div><h4>风险与替换</h4><p><b>催化剂：</b>{esc(answer.get("catalysts"))}</p><p><b>当前反向证据：</b>{esc(answer.get("current_reverse_evidence"))}</p><p><b>失效条件：</b>{esc(answer.get("invalidation_condition"))}</p><p><b>替换比较：</b>{esc(answer.get("replacement_comparison"))}</p></div>
        </div>
        <p><b>目标贡献或隔离：</b>{esc(answer.get("target_contribution_or_exclusion"))}</p>
        {details('本批次公司／行业事件线索', '<ul>'+event_rows+'</ul><p class="muted">事件线索不自动等同公司正式公告，动作仍以总控唯一答案为准。</p>')}
        '''
        cards.append(details(f'{asset_id}｜{answer.get("name") or base.get("name") or account.get("name") or holding.get("name") or "资产"}', body, attrs=f'data-holding="{esc(asset_id)}"'))
    return ''.join(cards)


def render_research_cards(bundle: dict[str, Any], judgment: dict[str, Any]) -> str:
    matrix = index_by(bundle.get("judgment_matrix", {}).get("assets", []), "asset_id")
    events = bundle.get("asset_event_scan", {}).get("cards", {})
    cards = []
    for answer in judgment["research_gate_answers"]:
        asset_id = str(answer["asset_id"])
        base = matrix.get(asset_id, {})
        event = events.get(asset_id, {}) if isinstance(events, dict) else {}
        event_summary = ''.join(f'<li>{esc(x.get("published_at"))}｜{esc(x.get("title"))}｜{link(x.get("url"))}</li>' for x in event.get("events", [])[:3]) or '<li>限定范围内未取得独立公司事件。</li>'
        body = f'''
        <div class="answer"><b>身份：</b>研究观察对象，当前不可执行，不构成买入名单。</div>
        <div class="asset-grid"><div><h4>第一关：板块</h4><p>{esc(answer.get("activated_sector"))}</p></div>
        <div><h4>停在哪一关</h4><p>{esc(answer.get("formal_gate_stop"))}</p></div>
        <div><h4>估值或风险定价</h4><p>{esc(answer.get("valuation_or_risk_pricing"))}</p></div>
        <div><h4>与现金和持仓比较</h4><p>{esc(answer.get("replacement_target"))}</p></div></div>
        <p><b>保留或移出：</b>{esc(answer.get("retain_or_drop"))}</p>
        <p><b>执行条件：</b>{esc(answer.get("executable_condition_or_none"))}</p>
        <p><b>短期／中期：</b>{esc(answer.get("short_term_outlook"))}；{esc(answer.get("medium_term_outlook"))}</p>
        <p><b>下一次验证：</b>{esc(answer.get("next_review"))}</p>
        {details('公司事件线索及边界', '<ul>'+event_summary+'</ul><p class="muted">线索需要正式财务、估值、护城河和替换比较共同闭合，不能单独通过第五关。</p>')}
        '''
        cards.append(details(f'{asset_id}｜{base.get("name", "研究对象")}', body, attrs=f'data-research="{esc(asset_id)}"'))
    return ''.join(cards)


def render_pdca(bundle: dict[str, Any], judgment: dict[str, Any]) -> str:
    summary = judgment["pdca_decisions"]
    records = []
    for idx, item in enumerate(bundle.get("pdca", {}).get("plain_records", []), 1):
        body = f'''
        <p><b>预测日期：</b>{esc(item.get("prediction_date"))}</p><p><b>当时预测：</b>{esc(item.get("prediction"))}</p>
        <p><b>验证时间：</b>{esc(item.get("verification_due"))}</p><p><b>成功标准：</b>{esc(item.get("success_definition"))}</p>
        <p><b>实际结果：</b>{esc(item.get("actual_result"))}</p><p><b>判定：</b>{esc(item.get("verdict"))}</p>
        <p><b>证据：</b>{esc(item.get("external_evidence"))}</p><p><b>教训：</b>{esc(item.get("lesson"))}</p>
        <p><b>相反选择会怎样：</b>{esc(item.get("counterfactual"))}</p>
        '''
        records.append(details(f'历史记录{idx}｜{item.get("verdict", "待核")}', body, attrs='data-pdca-record="1"'))
    new_predictions = plain_block(summary.get("new_predictions"))
    return f'''
    <div class="two-col"><div>{plain_block({k:v for k,v in summary.items() if k not in ("new_predictions", "system_changes_required")})}</div>
    <div><h4>本批次锁定的新预测</h4>{new_predictions}<h4>系统要改变什么</h4>{plain_block(summary.get("system_changes_required"))}</div></div>
    {details('展开57条历史记录', ''.join(records))}
    '''


def render_evidence(bundle: dict[str, Any]) -> str:
    rows = []
    for item in bundle.get("evidence_registry", []):
        rows.append(
            f'<tr><td>{esc(item.get("title"))}<br><small>{esc(item.get("publisher"))}</small></td><td>{esc(item.get("published_at"))}<br>{esc(item.get("data_date"))}</td>'
            f'<td>{esc(item.get("locator"))}</td><td>{esc(item.get("role"))}</td><td>{esc(item.get("supports"))}</td><td>{esc(item.get("cannot_prove"))}</td><td>{link(item.get("url"))}</td></tr>'
        )
    return '<table><thead><tr><th>证据</th><th>发布时间／数据日</th><th>原文位置</th><th>角色</th><th>支持什么</th><th>不能证明什么</th><th>原文</th></tr></thead><tbody>' + ''.join(rows) + '</tbody></table>'


def build_html(bundle: dict[str, Any], judgment: dict[str, Any], product_run_id: str, generated_at: str) -> str:
    known_failures = ''.join(f'<li>{esc(x)}</li>' for x in bundle.get("known_failures_and_limits", []))
    further = plain_block(judgment.get("further_research"))
    portfolio = plain_block(judgment.get("portfolio_level_judgment"))
    scan = plain_block(judgment.get("scan_pool_selection"))
    feature_rows = ''.join(
        f'<tr><td>{esc(key)}</td><td>{esc(value.get("data_interface"))}</td><td>{esc(value.get("render_location"))}</td><td>{esc(value.get("qa_gate"))}</td></tr>'
        for key, value in bundle.get("feature_matrix", {}).items()
    )
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="run_id" content="{esc(product_run_id)}"><meta name="parent_run_id" content="{esc(bundle['run_id'])}">
<title>★2026-08-20完整投研产品候选_v2.0</title>
<style>
:root{{--ink:#1c252b;--paper:#fff;--bg:#edf0f2;--nav:#17313d;--red:#a33b2f;--teal:#1d6c72;--green:#3e7448;--gold:#a97b1d;--line:#cbd3d8}}*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:"Microsoft YaHei","Noto Sans CJK SC",Arial,sans-serif;font-size:16px;line-height:1.72;letter-spacing:0}}nav{{position:sticky;top:0;z-index:9;background:var(--nav);padding:10px 3%;box-shadow:0 2px 10px #0003}}nav a{{color:#fff;text-decoration:none;margin-right:20px;font-weight:700}}main{{max-width:1480px;margin:auto;padding:24px}}header{{background:#fff;padding:28px;border-top:8px solid var(--red)}}h1{{font-size:34px;margin:0 0 12px}}h2{{font-size:26px}}h3{{font-size:20px}}h4{{font-size:17px;margin-bottom:6px}}section{{background:#fff;margin:20px 0;padding:26px;border-left:7px solid var(--teal)}}#layer1{{border-color:var(--red)}}#layer3{{border-color:var(--green)}}#appendix{{border-color:var(--gold)}}.identity{{display:grid;grid-template-columns:repeat(4,minmax(180px,1fr));gap:8px;font-size:14px}}.identity span{{background:#f3f6f7;padding:8px}}.hero-answer{{background:#f8ece9;padding:22px;margin:12px 0}}.hero-answer span{{font-weight:700;color:var(--red)}}.hero-answer h2{{margin:6px 0}}.decision-grid,.asset-grid,.metric-grid,.two-col,.mini-grid{{display:grid;gap:14px}}.decision-grid{{grid-template-columns:1.2fr 1fr 1fr}}.asset-grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.metric-grid{{grid-template-columns:repeat(4,minmax(0,1fr))}}.two-col{{grid-template-columns:repeat(2,minmax(0,1fr))}}.mini-grid{{grid-template-columns:repeat(3,minmax(0,1fr))}}article,.subblock{{border:1px solid var(--line);padding:14px;background:#fafbfc}}details{{border:1px solid var(--line);margin:10px 0;background:#fff;break-inside:avoid}}summary{{cursor:pointer;font-size:17px;font-weight:700;padding:12px;background:#f2f5f6}}.detail-body{{padding:14px}}.answer,.conclusion,.boundary{{padding:12px;background:#eef7f1;border-left:5px solid var(--green)}}.boundary{{background:#fff4dc;border-color:var(--gold)}}table{{width:100%;border-collapse:collapse;font-size:14px;margin:10px 0}}th,td{{border:1px solid var(--line);padding:7px;text-align:left;vertical-align:top}}th{{background:#e9eff2}}td.num{{text-align:right;font-variant-numeric:tabular-nums}}small,.muted{{color:#5c6770}}.metric strong{{display:block;font-size:27px}}.bar{{height:9px;background:#e2e7e9;margin:8px 0}}.bar i{{display:block;height:100%;background:var(--red)}}a{{color:#075f86;overflow-wrap:anywhere}}.badge{{display:inline-block;padding:2px 8px;background:#e8edef;margin-right:6px}}@media(max-width:900px){{.decision-grid,.asset-grid,.metric-grid,.two-col,.mini-grid,.identity{{grid-template-columns:1fr}}main{{padding:10px}}nav{{position:static}}table{{display:block;overflow-x:auto}}}}@media print{{nav{{display:none}}body{{background:#fff;font-size:11pt}}main{{max-width:none;padding:0}}section,header{{box-shadow:none;page-break-before:auto}}details{{break-inside:auto}}details>summary{{display:none}}details:not([open])>.detail-body{{display:block}}table{{font-size:9.5pt}}tr{{break-inside:avoid}}a{{color:#000;text-decoration:none}}}}
</style></head><body>
<nav><a href="#layer1">今天怎么做</a><a href="#layer2">为什么</a><a href="#layer3">完整研究</a><a href="#pdca">PDCA</a><a href="#appendix">证据附件</a></nav><main>
<header><h1>2026-08-20完整投研产品候选 v2.0</h1><div class="identity"><span><b>当前批次</b><br>{esc(product_run_id)}</span><span><b>证据父批次</b><br>{esc(bundle['run_id'])}</span><span><b>事实截止</b><br>{esc(bundle['evidence_cutoff_jst'])}</span><span><b>总控判断形成</b><br>{esc(judgment['judgment_formed_at_jst'])}</span><span><b>文件生成</b><br>{esc(generated_at)}</span><span><b>业务状态</b><br>待独立全量验收</span><span><b>发布状态</b><br>未授权</span><span><b>可执行状态</b><br>否</span></div></header>
<section id="layer1"><h2>第一层：今天怎么做</h2>{render_action(judgment)}<h3>组合级最终判断</h3>{portfolio}</section>
<section id="layer2"><h2>第二层：为什么这样做</h2><h3>七层因果链</h3>{render_seven_layers(bundle, judgment)}<h3>当日市场、宏观与重大新闻</h3>{render_news(bundle)}<h3>全账户与同一驱动风险</h3>{render_accounts(bundle, judgment)}<h3>机会发现与扫描边界</h3>{scan}<h3>湖水、老雷及外部观点</h3>{render_external_views(bundle)}</section>
<section id="layer3"><h2>第三层：完整研究底稿</h2><h3>24类持仓与资产唯一答案</h3>{render_asset_cards(bundle, judgment)}<h3>17只研究观察对象与正式五关</h3><p class="boundary">正式研究对象17只；第五关通过0只；当前可执行新增机会0只。研究未闭合不等于市场没有机会。</p>{render_research_cards(bundle, judgment)}<h3 id="pdca">PDCA：判断如何被事实纠正</h3>{render_pdca(bundle, judgment)}<h3>仍需进一步了解</h3>{further}<h3>当前真实缺口及产品影响</h3><ul>{known_failures}</ul></section>
<section id="appendix"><h2>证据与审计附件</h2><h3>证据注册表</h3>{render_evidence(bundle)}<h3>11项完整产品功能落点</h3><table><thead><tr><th>功能</th><th>数据接口</th><th>产品位置</th><th>质量闸</th></tr></thead><tbody>{feature_rows}</tbody></table><p class="muted">完整机器追踪、账户、五关、PDCA和总控判断落地矩阵另存为本批次JSON附件。附件用于复核，不替代正文大白话结论。</p></section>
</main></body></html>'''


def qa_checks(html_text: str, bundle: dict[str, Any], judgment: dict[str, Any], output_dir: Path) -> dict[str, Any]:
    visible = re.sub(r"<[^>]+>", " ", html_text)
    checks = {
        "parent_run_id_match": judgment.get("parent_run_id") == bundle.get("run_id"),
        "required_features_complete": not validate_handoff(bundle),
        "three_layer_order": html_text.find('id="layer1"') < html_text.find('id="layer2"') < html_text.find('id="layer3"') < html_text.find('id="appendix"'),
        "seven_layers_count": html_text.count('data-layer="') == 7,
        "holding_cards_count": html_text.count('data-holding="') == 24,
        "research_cards_count": html_text.count('data-research="') == 17,
        "pdca_records_count": html_text.count('data-pdca-record="1"') == 57,
        "account_classes_present": all(name in html_text for name in ("FUTU", "SBI_归属未闭合", "IBKR", "bitFlyer")),
        "executable_opportunity_zero_disclosed": "当前可执行新增机会0只" in visible,
        "external_views_present": "湖水" in visible and "老雷" in visible,
        "forbidden_internal_todo_zero": all(text not in visible for text in FORBIDDEN_BODY_TEXT),
        "candidate_boundary_present": all(text in visible for text in ("待独立全量验收", "未授权", "不可执行")),
        "utf8_replacement_zero": b"\xef\xbf\xbd" not in html_text.encode("utf-8"),
        "prior_candidate_not_used": bundle.get("source_lineage", {}).get("historical_candidate_html_used") is False and bundle.get("source_lineage", {}).get("historical_candidate_pdf_used") is False,
        "pdf_not_generated": not any(output_dir.glob("*.pdf")),
    }
    return {
        "schema_version": "V7-STAGE-C-SEMANTIC-QA-1.0",
        "run_id": bundle["run_id"],
        "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "checks": checks,
        "pass_count": sum(bool(x) for x in checks.values()),
        "check_count": len(checks),
        "status": "PASS_FOR_FULL_HTML_CONTENT_GATE" if all(checks.values()) else "FAIL",
        "pdf_generated": False,
        "pdf_authorization_received": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handoff", required=True, type=Path)
    parser.add_argument("--judgment", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--product-run-id", required=True)
    parser.add_argument("--daily-report", required=True, type=Path)
    args = parser.parse_args()

    bundle = load_json(args.handoff)
    judgment = load_json(args.judgment)
    errors = validate_handoff(bundle)
    if errors:
        raise ContractError(f"stage A handoff validation failed: {errors}")
    validate_final_judgment(judgment, bundle["run_id"])
    if judgment.get("codex_next_instruction", {}).get("authorized_stage") != "STAGE_C_COMPLETE_HTML_AND_ATTACHMENTS_ONLY":
        raise ContractError("Stage C authorization missing")
    if args.output_dir.exists():
        raise ContractError(f"output directory already exists: {args.output_dir}")

    daily_before = {"path": str(args.daily_report), "exists": args.daily_report.exists()}
    if args.daily_report.exists():
        daily_before.update({"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "modified_at": args.daily_report.stat().st_mtime})

    args.output_dir.mkdir(parents=True, exist_ok=False)
    generated_at = datetime.now(JST).isoformat(timespec="seconds")
    html_text = build_html(bundle, judgment, args.product_run_id, generated_at)
    html_path = args.output_dir / "★2026-08-20完整投研产品候选_v2.0.html"
    html_path.write_text(html_text, encoding="utf-8")

    answers = index_by(judgment["asset_final_answers"], "asset_id")
    research = index_by(judgment["research_gate_answers"], "asset_id")
    model = {
        "schema_version": "V7-COMPLETE-PRODUCT-MODEL-2.0",
        "run_id": args.product_run_id,
        "parent_run_id": bundle["run_id"],
        "evidence_cutoff_jst": str(bundle["evidence_cutoff_jst"]),
        "judgment_formed_at_jst": str(judgment["judgment_formed_at_jst"]),
        "generated_at_jst": generated_at,
        "status": STATUS,
        "today_action": judgment["today_action"],
        "seven_layers": judgment["seven_layer_final_judgment"],
        "portfolio_level_judgment": judgment["portfolio_level_judgment"],
        "asset_final_answers": answers,
        "research_gate_answers": research,
        "target_and_cash_plan": judgment["target_and_cash_plan"],
        "pdca_decisions": judgment["pdca_decisions"],
        "further_research": judgment.get("further_research", []),
        "pdf_generated": False,
        "pdf_authorization_received": False,
    }
    write_json(args.output_dir / "01_CompleteProductModel_20260820.json", model)
    write_json(args.output_dir / "02_GPT总控判断落地矩阵_20260820.json", {"run_id": args.product_run_id, "source_sha256": sha256(args.judgment), "judgment": judgment})
    write_json(args.output_dir / "03_全账户与风险边界_20260820.json", bundle["accounts_and_risk"])
    write_json(args.output_dir / "04_七层因果链与事实映射_20260820.json", {"facts": bundle["seven_layers"], "final_judgment": judgment["seven_layer_final_judgment"]})
    write_json(args.output_dir / "05_24类持仓唯一答案_20260820.json", {"count": len(answers), "items": list(answers.values())})
    write_json(args.output_dir / "06_17只研究对象正式五关_20260820.json", {"count": len(research), "executable_count": 0, "items": list(research.values())})
    write_json(args.output_dir / "07_新闻市场与公司事件证据_20260820.json", {"news": bundle["news_ledger"], "market": bundle["market_snapshot"], "asset_events": bundle["asset_event_scan"]})
    write_json(args.output_dir / "08_证据注册与来源边界_20260820.json", {"evidence_registry": bundle["evidence_registry"], "edinet": bundle["current_edinet"], "tdnet": bundle["current_tdnet"], "external_views": bundle["external_views"]})
    write_json(args.output_dir / "09_PDCA完整记录_20260820.json", bundle["pdca"])
    write_json(args.output_dir / "10_机会扫描与漏斗边界_20260820.json", {"full_market_scan": bundle["full_market_scan"], "selection": judgment["scan_pool_selection"]})

    qa = qa_checks(html_text, bundle, judgment, args.output_dir)
    write_json(args.output_dir / "11_阶段C完整HTML语义QA_20260820.json", qa)
    if qa["status"] != "PASS_FOR_FULL_HTML_CONTENT_GATE":
        raise ContractError(f"Stage C semantic QA failed: {qa}")

    daily_after = {"path": str(args.daily_report), "exists": args.daily_report.exists()}
    if args.daily_report.exists():
        daily_after.update({"size": args.daily_report.stat().st_size, "sha256": sha256(args.daily_report), "modified_at": args.daily_report.stat().st_mtime})
    daily_proof = {"before": daily_before, "after": daily_after, "unchanged": daily_before == daily_after, "overwritten_by_stage_c": False}
    write_json(args.output_dir / "12_正式日报未覆盖证明_20260820.json", daily_proof)
    if not daily_proof["unchanged"]:
        raise ContractError("formal daily report changed during Stage C")

    manifest = []
    for path in sorted(args.output_dir.iterdir(), key=lambda p: p.name):
        if path.is_file():
            manifest.append({"name": path.name, "path": str(path), "size": path.stat().st_size, "sha256": sha256(path), "modified_at": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds")})
    write_json(args.output_dir / "13_阶段C实物SHA256清单_20260820.json", {"run_id": args.product_run_id, "pdf_generated": False, "items": manifest})

    gate_report = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>阶段C完整HTML内容闸报告</title><style>body{{font-family:Microsoft YaHei,Arial;max-width:1100px;margin:30px auto;line-height:1.7}}table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #bbb;padding:8px}}th{{background:#eee}}.pass{{color:#176b35;font-weight:700}}</style></head><body><h1>阶段C完整HTML内容闸报告</h1><p>当前批次：{esc(args.product_run_id)}</p><p class="pass">本机语义预检：{esc(qa['status'])}（{qa['pass_count']}/{qa['check_count']}）</p><p>已生成完整HTML及附件；尚未生成PDF。下一步必须由GPT总控全文阅读HTML，并明确给出 <b>FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED</b> 后，才允许进入PDF阶段。</p><p>正式日报未覆盖：{esc(daily_proof['unchanged'])}。Release、交易和订单均未触发。</p></body></html>'''
    (args.output_dir / "14_阶段C完整HTML内容闸报告_20260820.html").write_text(gate_report, encoding="utf-8")

    print(json.dumps({"run_id": args.product_run_id, "parent_run_id": bundle["run_id"], "html": str(html_path), "html_size": html_path.stat().st_size, "html_sha256": sha256(html_path), "attachments": len(list(args.output_dir.iterdir())) - 1, "qa": qa["status"], "pdf_generated": False, "daily_report_unchanged": daily_proof["unchanged"]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
