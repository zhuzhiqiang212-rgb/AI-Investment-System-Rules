from __future__ import annotations

import argparse
import html
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .contracts import ContractError, load_json, validate_final_judgment, write_json

JST = timezone(timedelta(hours=9))
FORBIDDEN_TEXT = ("等待GPT总控", "需GPT总控决定", "仅供总控选择", "PENDING_JUDGMENT")


def e(value) -> str:
    return html.escape(str(value if value is not None else "尚未取得"))


def card(title: str, body: str, open_: bool = False) -> str:
    return f'<details {"open" if open_ else ""}><summary>{e(title)}</summary>{body}</details>'


def list_items(values) -> str:
    if not values:
        return "<p>本批次尚未取得可用内容，因此不据此形成动作。</p>"
    return "<ul>" + "".join(f"<li>{e(v)}</li>" for v in values) + "</ul>"


def render(bundle: dict, judgment: dict) -> tuple[dict, str]:
    answers = judgment["asset_final_answers"]
    if isinstance(answers, list):
        by_symbol = {str(item["asset_id"]): item for item in answers}
    else:
        by_symbol = answers
    model = {
        "schema_version": "V7-COMPLETE-PRODUCT-MODEL-2.0",
        "run_id": bundle["run_id"],
        "evidence_cutoff_jst": bundle["evidence_cutoff_jst"],
        "judgment_formed_at_jst": judgment.get("judgment_formed_at_jst"),
        "generated_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "status": {"business_pass":"PENDING_INDEPENDENT_FULL_REVIEW","final_product_pass":"PENDING_INDEPENDENT_FULL_REVIEW","release_status":"NOT_AUTHORIZED","current_executable":False},
        "layers": {
            "action": judgment.get("today_action", {}),
            "reason": {"seven_layers": judgment["seven_layer_final_judgment"], "news": bundle["news_ledger"], "accounts": bundle["accounts_and_risk"], "targets": judgment["target_and_cash_plan"]},
            "research": {"asset_answers": by_symbol, "research_gates": judgment["research_gate_answers"], "pdca": judgment["pdca_decisions"], "evidence": bundle["evidence_registry"]},
        },
        "display_contract": {"plain_language":True,"machine_codes_in_appendix_only":True,"navigation":True,"expand_collapse":True},
    }
    action = model["layers"]["action"]
    action_body = "".join(f"<h3>{e(k)}</h3><p>{e(v)}</p>" for k,v in action.items()) if isinstance(action, dict) else f"<p>{e(action)}</p>"
    seven = "".join(card(str(layer.get("layer") or layer.get("name") or f"第{i}层"), f"<p><b>事实：</b>{e(layer.get('fact'))}</p><p><b>为什么：</b>{e(layer.get('reasoning'))}</p><p><b>影响：</b>{e(layer.get('impact'))}</p><p><b>动作：</b>{e(layer.get('action'))}</p><p><b>反向证据与改判：</b>{e(layer.get('counter_evidence'))}；{e(layer.get('invalidation'))}</p>") for i,layer in enumerate(judgment["seven_layer_final_judgment"],1))
    account_rows = "".join(f"<tr><td>{e(k)}</td><td>{e(v)}</td></tr>" for k,v in bundle["accounts_and_risk"].get("account_known_values_jpy",{}).items())
    assets = "".join(card(f"{symbol} {item.get('name','')}", f"<p><b>唯一答案：</b>{e(item.get('final_answer'))}</p><p><b>事实与推理：</b>{e(item.get('reasoning'))}</p><p><b>估值或风险定价：</b>{e(item.get('valuation'))}</p><p><b>短期／一年：</b>{e(item.get('short_term'))}；{e(item.get('one_year'))}</p><p><b>催化剂：</b>{e(item.get('catalysts'))}</p><p><b>当前反向证据：</b>{e(item.get('reverse_evidence'))}</p><p><b>失效条件：</b>{e(item.get('invalidation_condition'))}</p><p><b>验证：</b>{e(item.get('review_date'))}</p>") for symbol,item in by_symbol.items())
    gate_cards = "".join(card(str(symbol), f"<p>{e(value)}</p>") for symbol,value in judgment["research_gate_answers"].items()) if isinstance(judgment["research_gate_answers"],dict) else f"<p>{e(judgment['research_gate_answers'])}</p>"
    source_rows = "".join(f"<tr><td>{e(x.get('title'))}</td><td>{e(x.get('publisher'))}</td><td>{e(x.get('data_date'))}</td><td>{e(x.get('role'))}</td><td>{e(x.get('supports'))}</td><td>{e(x.get('cannot_prove'))}</td></tr>" for x in bundle["evidence_registry"])
    doc = f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>★{bundle['run_id']}完整投研产品候选</title><style>
body{{font-family:"Microsoft YaHei",Arial,sans-serif;margin:0;color:#1e252b;background:#f4f5f7;line-height:1.7}}nav{{position:sticky;top:0;background:#102638;color:white;padding:10px 4%;z-index:3}}nav a{{color:white;margin-right:18px}}main{{max-width:1320px;margin:auto;padding:24px}}section{{background:white;margin:18px 0;padding:22px;border-top:7px solid #1f6f8b}}#layer1{{border-color:#b8442e}}#layer2{{border-color:#1f6f8b}}#layer3{{border-color:#49754a}}details{{border:1px solid #ccd2d9;padding:10px;margin:8px 0}}summary{{font-weight:700;cursor:pointer}}table{{width:100%;border-collapse:collapse}}th,td{{border:1px solid #ccd2d9;padding:8px;text-align:left;vertical-align:top}}th{{background:#eef3f6}}.status{{background:#fff3cd;padding:12px}}@media print{{nav{{display:none}}details{{break-inside:avoid}}details>summary{{display:none}}details:not([open])>*:not(summary){{display:block}}}}</style></head><body><nav><a href="#layer1">今天怎么做</a><a href="#layer2">为什么</a><a href="#layer3">完整底稿</a><a href="#evidence">证据附件</a></nav><main>
<h1>完整投研产品候选</h1><div class="status">事实截止：{e(bundle['evidence_cutoff_jst'])}｜判断形成：{e(judgment.get('judgment_formed_at_jst'))}｜生成：{e(model['generated_at_jst'])}<br>候选待独立全量终验；未授权Release，不可执行，不构成订单。</div>
<section id="layer1"><h2>第一层：今天怎么做</h2>{action_body}</section>
<section id="layer2"><h2>第二层：为什么这样做</h2><h3>七层因果链</h3>{seven}<h3>全账户风险</h3><table><thead><tr><th>账户</th><th>已知资产（日元）</th></tr></thead><tbody>{account_rows}</tbody></table><h3>＋40%／＋100%目标路径</h3><p>{e(judgment['target_and_cash_plan'])}</p><h3>当日重大新闻</h3>{''.join(card(x['title'], f"<p>{e(x.get('fact'))}</p><p><b>使用边界：</b>{e(x.get('boundary'))}</p>") for x in bundle['news_ledger']['records'])}</section>
<section id="layer3"><h2>第三层：完整研究底稿</h2><h3>全部持仓与资产唯一答案</h3>{assets}<h3>正式五关与研究对象</h3>{gate_cards}<h3>PDCA</h3><p>{e(judgment['pdca_decisions'])}</p><h3>仍需进一步了解</h3>{list_items(judgment.get('further_research'))}</section>
<section id="evidence"><h2>证据与审计附件</h2><table><thead><tr><th>标题</th><th>机构</th><th>数据日</th><th>角色</th><th>实际支持</th><th>不能证明</th></tr></thead><tbody>{source_rows}</tbody></table></section>
</main></body></html>'''
    hits = [text for text in FORBIDDEN_TEXT if text in doc]
    if hits:
        raise ContractError(f"unfinished internal instructions in product HTML: {hits}")
    return model, doc


def main() -> int:
    parser=argparse.ArgumentParser()
    parser.add_argument("--handoff",required=True,type=Path)
    parser.add_argument("--judgment",required=True,type=Path)
    parser.add_argument("--output-dir",required=True,type=Path)
    args=parser.parse_args()
    bundle=load_json(args.handoff)
    judgment=load_json(args.judgment)
    validate_final_judgment(judgment,bundle["run_id"])
    model,doc=render(bundle,judgment)
    args.output_dir.mkdir(parents=True,exist_ok=False)
    write_json(args.output_dir/"CompleteProductModel.json",model)
    (args.output_dir/"完整投研产品候选.html").write_text(doc,encoding="utf-8")
    print(json.dumps({"run_id":bundle["run_id"],"html":str(args.output_dir/"完整投研产品候选.html"),"pdf_generated":False},ensure_ascii=False))
    return 0

if __name__=="__main__":
    raise SystemExit(main())