from __future__ import annotations

import argparse
import html
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from .contracts import REQUIRED_FEATURES, load_json, sha256, validate_handoff, write_json

JST = timezone(timedelta(hours=9))
ROOT = Path(r"G:\我的云端硬盘\AI_Investment_System")
TASK_CENTER = ROOT / "00_任务中心"

FEATURE_ROWS = {
    "three_layer_reading": ("CompleteProductModel.layers", "第一层行动驾驶舱／第二层因果解释／第三层研究底稿", "three_layer_semantic_gate"),
    "seven_layer_causal_chain": ("RunBundle.seven_layers + FinalJudgment.seven_layer_final_judgment", "第二层七层因果链与传导图", "seven_layer_transmission_gate"),
    "same_day_news_and_research": ("RunBundle.news_ledger/asset_event_scan/external_views", "第二层当日新闻与外部观点", "news_cutoff_and_failure_gate"),
    "all_accounts_and_assets": ("RunBundle.accounts_and_risk", "第一层账户状态＋第三层全账户表", "account_reconciliation_gate"),
    "holding_deep_research": ("RunBundle.holding_inputs + FinalJudgment.asset_final_answers", "第三层逐只持仓深研", "holding_completeness_gate"),
    "formal_five_gates_and_discovery": ("RunBundle.formal_gates/full_market_scan + FinalJudgment.research_gate_answers", "第三层五关漏斗与研究对象", "five_gate_sequence_gate"),
    "target_paths_40_100": ("RunBundle.accounts_and_risk/annual_target_boundary + FinalJudgment.target_and_cash_plan", "第二层目标路径图", "target_math_and_baseline_gate"),
    "evidence_chain": ("RunBundle.evidence_registry", "第三层末尾证据附件", "evidence_role_support_gate"),
    "pdca_learning_loop": ("RunBundle.pdca + FinalJudgment.pdca_decisions", "第三层PDCA正文与历史附件", "pdca_external_result_gate"),
    "historical_important_functions": ("RunBundle.historical_function_register", "三层对应位置＋附件", "historical_function_exit_gate"),
    "plain_language_experience": ("CompleteProductModel.display_contract", "全产品导航、展开折叠、图表与大白话", "readability_sampling_gate"),
}


def read_pdf_excerpt(path: Path, limit: int = 5000) -> str:
    reader = PdfReader(str(path))
    text = "\n".join((page.extract_text() or "").strip() for page in reader.pages)
    return text[:limit]


def evidence_record(path: Path, role: str, title: str | None = None) -> dict:
    stat = path.stat()
    return {
        "title": title or path.name,
        "publisher": "项目本地正式实物",
        "path": str(path),
        "published_at": None,
        "data_date": None,
        "retrieved_at_jst": datetime.fromtimestamp(stat.st_mtime, JST).isoformat(timespec="seconds"),
        "locator": "完整文件",
        "role": role,
        "supports": "支持该文件所登记的结构化事实；具体结论仍须逐字段核对。",
        "cannot_prove": "不能仅凭文件存在证明投资判断、当日事件或最终动作。",
        "freshness": "按文件数据日期和本批次截止时间单独判断",
        "sha256": sha256(path),
        "size": stat.st_size,
    }


def parse_tdnet(path: Path, tracked_codes: set[str]) -> dict:
    soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
    matches = []
    for row in soup.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 4:
            continue
        code = cells[1].get_text(" ", strip=True)
        ticker = code[:4] if len(code) >= 4 else code
        if ticker not in tracked_codes:
            continue
        link = cells[3].find("a")
        href = link.get("href") if link else None
        matches.append({
            "time_jst": cells[0].get_text(" ", strip=True),
            "security_code": code,
            "name": cells[2].get_text(" ", strip=True),
            "title": cells[3].get_text(" ", strip=True),
            "url": f"https://www.release.tdnet.info/inbs/{href}" if href else None,
            "source": "TDnet official daily disclosure list",
        })
    return {
        "source_url": "https://www.release.tdnet.info/inbs/I_list_001_20260820.html",
        "raw_path": str(path),
        "raw_sha256": sha256(path),
        "tracked_company_count": len(tracked_codes),
        "matched_disclosures": matches,
        "matched_count": len(matches),
        "boundary": "当日列表零命中仅表示该列表范围未发现对应代码，不等于公司没有其他正式披露。",
    }


def build_external_views(base_path: Path) -> dict:
    base = load_json(base_path)
    records = list(base.get("records", []))
    existing = {str(item.get("path")) for item in records}
    additions = []
    for path in sorted(Path(r"G:\我的云端硬盘\湖水资讯").glob("26-08-20-*.pdf")):
        if str(path) in existing:
            continue
        additions.append({
            "path": str(path), "exists": True, "source_group": "湖水", "read_status": "已读取",
            "size": path.stat().st_size, "sha256": sha256(path),
            "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds"),
            "text_excerpt": read_pdf_excerpt(path),
            "use_boundary": "外部研究观点，只能支持或反对总控判断，不能冒充当日官方事实或单独形成交易动作。",
        })
    for path in sorted((ROOT / "data" / "external" / "text").glob("26-08-[345]-*老雷*.txt")):
        if str(path) in existing:
            continue
        additions.append({
            "path": str(path), "exists": True, "source_group": "老雷", "read_status": "已读取",
            "size": path.stat().st_size, "sha256": sha256(path),
            "modified_at_jst": datetime.fromtimestamp(path.stat().st_mtime, JST).isoformat(timespec="seconds"),
            "text_excerpt": path.read_text(encoding="utf-8", errors="replace")[:5000],
            "use_boundary": "历史外部观点，必须披露材料日期和时效；不能冒充生产日事实。",
        })
    records.extend(additions)
    return {
        "records": records,
        "count": len(records),
        "lake_count": sum(item.get("source_group") == "湖水" for item in records),
        "laolei_count": sum(item.get("source_group") == "老雷" for item in records),
        "added_after_original_foundation": len(additions),
        "judgment_fields": ["具体观点", "支持或反对的判断", "影响资产", "采用与否", "动作变化", "验证时间"],
    }


def build_news_ledger(run_id: str, cutoff: str, market: dict, fed_pdf: Path, gdp_pdf: Path) -> dict:
    records = [
        {
            "event_id": "NEWS-20260820-FOMC-MINUTES",
            "title": "2026年7月28日至29日FOMC会议纪要",
            "publisher": "Federal Reserve Board",
            "published_at": "2026-08-19T14:00:00-04:00",
            "data_date": "2026-07-28/2026-07-29",
            "retrieved_at_jst": cutoff,
            "url": "https://www.federalreserve.gov/monetarypolicy/files/fomcminutes20260729.pdf",
            "local_path": str(fed_pdf),
            "locator": "会议纪要正文；需由GPT总控引用具体段落",
            "fact": "正式纪要已取得；通胀若不回落时的进一步收紧风险必须进入利率和高估值资产判断。",
            "boundary": "纪要证明会议讨论，不等于未来加息已经决定。",
            "sha256": sha256(fed_pdf),
        },
        {
            "event_id": "NEWS-20260820-TREASURY-BUYBACK-OIL",
            "title": "美国财政部扩大长期国债回购，油价因中东风险上升",
            "publisher": "Associated Press",
            "published_at": "2026-08-20T05:13:33Z",
            "data_date": "2026-08-20",
            "retrieved_at_jst": cutoff,
            "url": "https://apnews.com/article/1dcf7c9c3cc490b82b2632302628c46b",
            "locator": "全文市场综述",
            "fact": "财政部回购有助于阶段性缓解长债收益率压力；布伦特与WTI上涨则抬高通胀和长端利率风险。",
            "boundary": "独立市场来源，不替代财政部操作文件；价格是报道时点，不是本批次最终行情。",
        },
        {
            "event_id": "NEWS-20260820-JAPAN-GDP",
            "title": "日本2026年4至6月GDP第一次初步估计",
            "publisher": "日本内阁府经济社会综合研究所",
            "published_at": "2026-08-17T08:50:00+09:00",
            "data_date": "2026-Q2",
            "retrieved_at_jst": cutoff,
            "url": "https://www.esri.cao.go.jp/en/sna/kouhyou/kouhyou_top.html",
            "local_path": str(gdp_pdf),
            "locator": "官方季度GDP发布实物",
            "fact": "官方GDP实物已取得，用于日本增长、BOJ和日股资金判断。",
            "boundary": "属于8月17日已公开宏观事实，不是8月20日新发生事件。",
            "sha256": sha256(gdp_pdf),
        },
        {
            "event_id": "NEWS-20260820-MARKET-SNAPSHOT",
            "title": "本批次宏观市场行情快照",
            "publisher": "Yahoo Finance公开图表接口",
            "published_at": None,
            "data_date": "2026-08-20",
            "retrieved_at_jst": market.get("finished_at_jst"),
            "url": None,
            "locator": "06_宏观市场行情快照_20260820.json逐项时间字段",
            "fact": "股指、美元/日元、美国10年与30年收益率、油价、黄金和加密价格均按各自最后可得市场时间登记。",
            "boundary": "未收盘市场只代表盘中；TOPIX自动源失败必须单列。",
        },
    ]
    return {
        "run_id": run_id,
        "search_started_at_jst": "2026-08-20T22:15:00+09:00",
        "search_finished_at_jst": cutoff,
        "search_scope": ["全球市场", "美联储与美国财政部", "日本GDP/BOJ/日元", "油价与霍尔木兹风险", "AI与数据中心", "41项资产公司事件"],
        "queries": [
            "2026-08-20 global markets Fed yields dollar yen oil",
            "2026-08-20 Japan BOJ yen markets",
            "2026-08-20 Fed minutes inflation rates",
            "2026-08-20 AI semiconductor data center",
        ],
        "records": records,
        "failed_sources": ["Reuters直接页未稳定返回；使用Fed官方纪要、AP及可读取交叉来源，未把失败写成无新闻。"],
        "excluded": ["截止时间之后发布的事实", "只有标题而无可核内容的线索", "与账户、持仓、目标或七层无直接关系的低影响消息"],
    }


def html_table(rows: list[dict], columns: list[tuple[str, str]]) -> str:
    head = "".join(f"<th>{html.escape(label)}</th>" for _, label in columns)
    body = []
    for row in rows:
        body.append("<tr>" + "".join(f"<td>{html.escape(str(row.get(key, '')))}</td>" for key, _ in columns) + "</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def render_handoff(payload: dict) -> str:
    matrix_rows = [{"功能": k, **v} for k, v in payload["feature_matrix"].items()]
    accounts = [{"账户": k, "已知资产日元": v} for k, v in payload["accounts_and_risk"]["account_known_values_jpy"].items()]
    layer_rows = []
    for index, layer in enumerate(payload["seven_layers"], start=1):
        layer_rows.append({"序号": index, "层级": layer.get("layer") or layer.get("name") or layer.get("title"), "事实输入": str(layer.get("facts") or layer.get("fact") or "已登记"), "待总控判断": str(layer.get("judgment_required", True))})
    return f'''<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>V7 v2.0 GPT总控唯一业务判断输入包 Current</title><style>
body{{font-family:"Microsoft YaHei",Arial,sans-serif;margin:0;background:#f6f7f9;color:#1d2329;line-height:1.65}}main{{max-width:1320px;margin:auto;padding:28px}}h1{{font-size:28px}}h2{{border-left:5px solid #1868b7;padding-left:10px;margin-top:32px}}.status{{background:#fff4d6;border:1px solid #e6b94a;padding:14px}}table{{border-collapse:collapse;width:100%;background:white;margin:12px 0}}th,td{{border:1px solid #ccd2d9;padding:8px;vertical-align:top;text-align:left}}th{{background:#eef3f8}}details{{background:white;border:1px solid #d8dde3;margin:10px 0;padding:10px}}code{{white-space:pre-wrap;word-break:break-word}}.bad{{color:#a12720;font-weight:700}}.good{{color:#146b3a;font-weight:700}}</style></head><body><main>
<h1>V7 v2.0 GPT总控唯一业务判断输入包 Current</h1>
<div class="status"><b>阶段状态：</b>{html.escape(payload['status'])}<br><b>run_id：</b>{html.escape(payload['run_id'])}<br><b>统一证据截止：</b>{html.escape(payload['evidence_cutoff_jst'])}<br><b>边界：</b>本文件是唯一业务判断交接，不是产品、不是Release，也没有生成PDF。</div>
<h2>一、完整功能机器矩阵</h2>{html_table(matrix_rows, [('功能','功能'),('plain_name','中文功能'),('data_interface','数据接口'),('render_location','渲染位置'),('qa_gate','语义闸'),('stage_a_status','阶段A状态')])}
<h2>二、全账户与风险边界</h2>{html_table(accounts,[('账户','账户'),('已知资产日元','已知资产日元')])}<p>{html.escape(payload['accounts_and_risk'].get('annual_performance_boundary',''))}</p>
<h2>三、七层事实输入</h2>{html_table(layer_rows,[('序号','序号'),('层级','层级'),('事实输入','事实输入'),('待总控判断','待总控判断')])}
<h2>四、正式五关和全市场扫描</h2><p>正式五关原文已锁定；全市场扫描是同日原始/财务筛选，不会机械升级为可执行机会。</p><details open><summary>五关结构</summary><code>{html.escape(json.dumps(payload['formal_gates'],ensure_ascii=False,indent=2))}</code></details>
<h2>五、当日新闻、公司事件与外部观点</h2><p>新闻检索起止时间真实不同；失败源单列。41项资产公司事件检索结果是线索，正式披露与判断角色分离。</p><details><summary>重大新闻账本</summary><code>{html.escape(json.dumps(payload['news_ledger'],ensure_ascii=False,indent=2))}</code></details><details><summary>湖水／老雷材料</summary><code>{html.escape(json.dumps(payload['external_views'],ensure_ascii=False,indent=2))}</code></details>
<h2>六、一次性待GPT总控判断矩阵</h2><p class="bad">以下字段必须由GPT总控一次性完成；Codex没有填写投资判断、概率、倍数、买卖或仓位动作。</p><details open><summary>判断矩阵</summary><code>{html.escape(json.dumps(payload['judgment_matrix'],ensure_ascii=False,indent=2))}</code></details>
<h2>七、已知失败与隔离</h2><ul>{''.join('<li>'+html.escape(str(x))+'</li>' for x in payload['known_failures_and_limits'])}</ul>
<h2>八、安全状态</h2><code>{html.escape(json.dumps(payload['safety'],ensure_ascii=False,indent=2))}</code>
</main></body></html>'''


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--cutoff", required=True)
    parser.add_argument("--base-handoff", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    base = load_json(args.base_handoff.resolve())
    futu = load_json(run_dir / "02_OpenD标准化账户快照_20260820.json")
    recon = load_json(run_dir / "03_富途账户勾稽报告_20260820.json")
    quotes = load_json(run_dir / "05_41资产及汇率行情快照_20260820.json")
    market = load_json(run_dir / "06_宏观市场行情快照_20260820.json")
    accounts = load_json(run_dir / "07_全账户持仓合并与风险观察_20260820.json")
    edinet = load_json(run_dir / "08_EDINET当日只读查询_20260820.json")
    company_events = load_json(run_dir / "09_41项资产公司事件增量检索_20260820.json")
    external = build_external_views(run_dir / "04_湖水老雷原文提取_20260820.json")
    tdnet = parse_tdnet(run_dir / "08_TDnet_20260820_raw.html", {"4063","4568","6758","6857","6954","7203","7974","8001","8306","8316","8411","8766","9984"})
    gdp_pdf = args.base_handoff.resolve().parent / "08_Japan_Q2_2026_GDP_official.pdf"
    if not gdp_pdf.exists():
        gdp_pdf = ROOT / "output" / "decision_inputs" / "2026-08-20" / "V7-V20-FOUNDATION-20260820-105724-JST" / "08_Japan_Q2_2026_GDP_official.pdf"
    fed_pdf = run_dir / "08_FOMC_minutes_20260729_official.pdf"
    news = build_news_ledger(args.run_id, args.cutoff, market, fed_pdf, gdp_pdf)

    scan_files = {name: ROOT / "data" / "screen" / name for name in ("_run2_20260820.json","universe_20260820.json","gate_20260820.json","candidates_20260820.json","funnel_compare_20260820.json")}
    scan = {key: {"path": str(path), "sha256": sha256(path), "payload": load_json(path)} for key, path in scan_files.items() if path.exists()}

    source_paths = [
        ROOT / "00_请先看这里" / "★开工必读_主控文件.html",
        ROOT / "00_请先看这里" / "★V7_Current知识库总索引_20260814.html",
        ROOT / "00_请先看这里" / "完整产品验收标准_20260722.html",
        ROOT / "00_请先看这里" / "完整产品_深度标准_v1.html",
        ROOT / "00_请先看这里" / "预测优先口径_概率分布与PDCA_v1_20260730.html",
        ROOT / "00_请先看这里" / "正式尺_总则第十三条之二_账户数据来源与目标管理_20260811.html",
        ROOT / "00_请先看这里" / "右栏_过滤标准筛选规则.html",
        ROOT / "00_请先看这里" / "右栏_板块地图.html",
    ]
    evidence_registry = [evidence_record(path, "Current规则或验收依据") for path in source_paths]
    for path in [run_dir / "01_OpenD原始只读返回_20260820.json", run_dir / "02_OpenD标准化账户快照_20260820.json", run_dir / "03_富途账户勾稽报告_20260820.json", run_dir / "05_41资产及汇率行情快照_20260820.json", run_dir / "06_宏观市场行情快照_20260820.json", run_dir / "07_全账户持仓合并与风险观察_20260820.json", run_dir / "08_EDINET当日只读查询_20260820.json", run_dir / "08_TDnet_20260820_raw.html", run_dir / "09_41项资产公司事件增量检索_20260820.json", fed_pdf, gdp_pdf]:
        evidence_registry.append(evidence_record(path, "本批次事实证据"))

    feature_matrix = {}
    for feature, (interface, location, gate) in FEATURE_ROWS.items():
        feature_matrix[feature] = {
            "plain_name": feature.replace("_", " "),
            "data_interface": interface,
            "render_location": location,
            "qa_gate": gate,
            "stage_a_status": "INTERFACE_AND_POSITION_DEFINED",
            "final_product_status": "WAITING_GPT_CONTROL_JUDGMENT",
        }

    formal_gates = base.get("formal_gates", {})
    if "definitions" in formal_gates:
        formal_gates = {**formal_gates, **{f"gate_{item['gate']}": item for item in formal_gates.get("definitions", [])}}
    layers = base.get("seven_layers", [])
    for layer in layers:
        layer["judgment_required"] = True
        layer["current_batch_evidence_cutoff_jst"] = args.cutoff

    payload = {
        "schema_version": "V7-COMPLETE-PRODUCT-RUN-BUNDLE-2.0",
        "run_id": args.run_id,
        "scan_run_id": (scan.get("_run2_20260820.json", {}).get("payload", {}) or {}).get("run_id", "V7-SCAN-20260820-111500-JST"),
        "status": "STAGE_A_COMPLETE_WAITING_SINGLE_GPT_CONTROL_JUDGMENT",
        "product_generated": False,
        "release_status": "NOT_AUTHORIZED",
        "current_executable": False,
        "evidence_cutoff_jst": args.cutoff,
        "generated_at_jst": datetime.now(JST).isoformat(timespec="seconds"),
        "single_pause_rule": "本文件是唯一一次GPT总控业务判断交接点。",
        "source_lineage": {
            "current_rules": "直接读取Current正式实物",
            "same_day_raw_evidence": str(run_dir),
            "same_day_fact_bundle_reused": str(args.base_handoff.resolve()),
            "historical_candidate_html_used": False,
            "historical_candidate_pdf_used": False,
            "boundary": "复用同日结构化事实和历史稳定财务/估值输入，不复制失败候选正文、布局或判断。",
        },
        "feature_matrix": feature_matrix,
        "formal_gates": formal_gates,
        "accounts_and_risk": accounts,
        "futu_reconciliation": recon,
        "market_snapshot": market,
        "asset_quotes": quotes,
        "news_ledger": news,
        "asset_event_scan": company_events,
        "external_views": external,
        "seven_layers": layers,
        "full_market_scan": scan,
        "current_edinet": edinet,
        "current_tdnet": tdnet,
        "holding_inputs": base.get("holding_external_facts_reused", base.get("holding_inputs", {})),
        "valuation_inputs": base.get("valuation_external_inputs_reused", base.get("valuation_inputs", {})),
        "pdca": base.get("pdca", {}),
        "annual_target_boundary": {
            **base.get("annual_target_boundary", {}),
            "current_rule": "缺少2026-01-01完整净值及净入出金，不计算年度真实完成度；富途与SBI前瞻观察基线分别展示。",
        },
        "historical_function_register": {
            "required": ["数据新鲜度", "昨日变化", "最重要风险", "组合体检", "替换引擎", "全市场五关漏斗", "估值/风险定价比较", "宏观强弱与证伪", "共同风险穿透", "确定性累积", "日周月季年复盘", "影子组合与不行动反事实", "规则与判断咬合", "逐只深研", "展开折叠导航"],
            "source": "Current验收标准、深度标准和本次正式施工令",
            "render_mapping_required": True,
        },
        "judgment_matrix": base.get("judgment_matrix", {}),
        "gpt_control_output_contract": {
            "output_path": str(TASK_CENTER / "V7_v2.0_GPT总控最终业务判断_Current.json"),
            "required_keys": ["parent_run_id", "judgment_formed_at_jst", "today_action", "seven_layer_final_judgment", "asset_final_answers", "research_gate_answers", "target_and_cash_plan", "pdca_decisions", "further_research"],
            "asset_key": "asset_id/symbol必须与本包judgment_matrix.assets逐项对应",
            "boundary": "GPT总控一次性完成业务判断；不得拆成向董事长逐项询问。"
        },
        "codex_continuation_instruction": "读取00_任务中心/V7_v2.0_GPT总控最终业务判断_Current.json，校验parent_run_id后继续同一任务阶段C，仅生成完整HTML及附件；未收到FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED前不得生成PDF。",
        "evidence_registry": evidence_registry,
        "known_failures_and_limits": [
            f"宏观行情自动源失败{market.get('failure_count',0)}项；失败项不解释为无行情。",
            "SBI个人/公司归属未闭合；IBKR与bitFlyer仅有确认无交易后的最后已知数量，当前现金、融资、费用仍不完整。",
            "TOPIX自动公开行情若失败，需总控按缺口边界判断，不用日经225冒充。",
            "公司事件RSS是线索，不等于正式披露；TDnet当日匹配与EDINET法定文件分别登记。",
            "全市场扫描在同日11:13至11:30执行，属于原始/财务筛选；正式板块激活和五关结果仍须GPT总控判断。",
            "2026年度真实完成度因1月1日净值和全年净入出金缺失不可精算。",
        ],
        "safety": {
            "pdf_generated": False,
            "html_product_generated": False,
            "trade_calls": 0,
            "order_calls": 0,
            "release_registered": False,
            "daily_report_overwritten": False,
            "pdf_authorization_required": "FULL_HTML_CONTENT_GATE_PASS / PDF_RENDER_AUTHORIZED",
        },
    }
    errors = validate_handoff(payload)
    payload["stage_a_gate"] = {"passed": not errors, "errors": errors, "checked_at_jst": datetime.now(JST).isoformat(timespec="seconds")}
    if errors:
        payload["status"] = "STAGE_A_BLOCKED"
    json_path = TASK_CENTER / "V7_v2.0_GPT总控唯一业务判断输入包_Current.json"
    html_path = TASK_CENTER / "V7_v2.0_GPT总控唯一业务判断输入包_Current.html"
    write_json(json_path, payload)
    html_path.write_text(render_handoff(payload), encoding="utf-8")
    write_json(run_dir / "00_完整功能矩阵_Current.json", feature_matrix)
    (run_dir / "00_完整功能矩阵_Current.html").write_text(render_handoff({**payload, "judgment_matrix": {"说明": "功能矩阵专页；完整判断矩阵见00_任务中心唯一输入包。"}}), encoding="utf-8")
    qa = {
        "run_id": args.run_id,
        "status": payload["status"],
        "checks": {
            "feature_count": len(feature_matrix),
            "required_feature_count": len(REQUIRED_FEATURES),
            "seven_layer_count": len(layers),
            "account_count": len(accounts.get("account_known_values_jpy", {})),
            "position_rows": len(accounts.get("positions", [])),
            "asset_quote_success": quotes.get("success_count"),
            "asset_quote_failures": quotes.get("failure_count"),
            "company_event_assets": company_events.get("counts", {}).get("assets"),
            "edinet_connected": edinet.get("verify", {}).get("ok"),
            "edinet_symbol_count": len(edinet.get("coverage", {}).get("symbols", {})),
            "tdnet_matched_count": tdnet.get("matched_count"),
            "scan_files": len(scan),
            "historical_candidate_dependency": False,
            "product_generated": False,
            "pdf_generated": False,
        },
        "errors": errors,
        "result": "STAGE_A_HARD_GATE_PASS" if not errors else "STAGE_A_HARD_GATE_FAIL",
    }
    write_json(run_dir / "10_阶段A完整功能与证据硬闸_20260820.json", qa)
    manifest_files = [p for p in run_dir.rglob("*") if p.is_file()] + [json_path, html_path]
    manifest = [{"path": str(p), "size": p.stat().st_size, "sha256": sha256(p)} for p in sorted(manifest_files)]
    write_json(run_dir / "11_阶段A实物SHA256清单_20260820.json", manifest)
    print(json.dumps({"status": payload["status"], "run_id": args.run_id, "handoff_json": str(json_path), "handoff_html": str(html_path), "qa_errors": errors, "manifest_count": len(manifest)}, ensure_ascii=False))
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())