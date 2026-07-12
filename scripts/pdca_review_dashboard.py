from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape(str(value))


def score_class(score: Any) -> str:
    try:
        number = int(score)
    except Exception:
        return "flat"
    if number > 0:
        return "up"
    if number < 0:
        return "down"
    return "flat"


def ring_card(item: dict[str, Any]) -> str:
    series = item.get("daily_score_series", [])
    chips = []
    for point in series:
        cls = score_class(point.get("daily_score"))
        chips.append(
            f"<span class='chip {cls}'>{esc(point.get('date'))}｜{esc(point.get('daily_score'))}｜{esc(point.get('current_certainty'))}</span>"
        )
    chips_html = "".join(chips) if chips else "<span class='muted'>待累积</span>"
    return f"""
    <section class="card">
      <div class="card-head">
        <h2>{esc(item.get('ring_name'))}</h2>
        <span class="certainty">{esc(item.get('current_certainty'))}</span>
      </div>
      <p class="judgment">判断：{esc(item.get('judgment'))}</p>
      <div class="score">累积分 <b>{esc(item.get('cumulative_score'))}</b></div>
      <div class="track">{chips_html}</div>
      <p class="muted">轨迹：{esc(item.get('certainty_path_text'))}</p>
    </section>
    """


def scale_panel(name: str, data: dict[str, Any]) -> str:
    if name == "日":
        status = data.get("status", "")
        detail = data.get("decision_quality", {}).get("reason", "")
    else:
        summary = data.get("summary", data)
        status = summary.get("status", "")
        detail = f"可用天数 {summary.get('days_available', 0)}；夯实 {len(summary.get('solidifying', []))}；动摇 {len(summary.get('shaking', []))}"
    return f"""
    <section class="scale">
      <h3>{esc(name)}复盘</h3>
      <p><b>{esc(status)}</b></p>
      <p>{esc(detail)}</p>
    </section>
    """


def build_html(review: dict[str, Any]) -> str:
    quality = review.get("today_decision_quality", {})
    cards = "\n".join(ring_card(item) for item in review.get("certainty_trajectories", []))
    multi = review.get("multi_scale", {})
    panels = "\n".join([
        scale_panel("日", multi.get("daily", {})),
        scale_panel("周", multi.get("weekly", {})),
        scale_panel("月", multi.get("monthly", {})),
        scale_panel("季", multi.get("quarterly", {})),
        scale_panel("年", multi.get("yearly", {})),
    ])
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>PDCA复盘看板</title>
  <style>
    body{{margin:0;background:#0d1620;color:#edf4f8;font-family:"Microsoft YaHei",Arial,sans-serif;line-height:1.65;}}
    .wrap{{max-width:1180px;margin:0 auto;padding:24px 18px 60px;}}
    header{{border:1px solid #294257;background:#122132;border-radius:10px;padding:18px 20px;margin-bottom:16px;}}
    h1{{margin:0 0 8px;font-size:24px;}}
    .sub{{color:#9fb5c8;font-size:13px;}}
    .quality{{font-size:18px;color:#ffcf6b;font-weight:700;}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px;}}
    .card,.scale{{background:#152332;border:1px solid #294257;border-radius:10px;padding:15px;}}
    .card-head{{display:flex;align-items:center;justify-content:space-between;gap:10px;border-bottom:1px solid #263a4b;padding-bottom:8px;}}
    h2,h3{{margin:0;color:#ffe2a8;}}
    .certainty{{background:#22394c;color:#8ed0ff;border-radius:999px;padding:3px 10px;font-size:13px;}}
    .judgment{{color:#d8e5ef;}}
    .score b{{font-size:24px;color:#ffcf6b;}}
    .track{{display:flex;flex-wrap:wrap;gap:7px;margin:10px 0;}}
    .chip{{border-radius:7px;padding:4px 8px;font-size:12px;background:#243448;color:#c9d6e2;}}
    .up{{background:#44222a;color:#ff8f9b;}}
    .down{{background:#173828;color:#7ee0a0;}}
    .flat{{background:#243448;color:#c9d6e2;}}
    .muted{{color:#8ea3b6;font-size:13px;}}
    .scales{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:16px;}}
  </style>
</head>
<body>
  <main class="wrap">
    <header>
      <h1>PDCA复盘看板</h1>
      <div class="quality">今天决策质量分={esc(quality.get('level'))}，原因：{esc(quality.get('reason'))}</div>
      <div class="sub">指纹：framework_fixed={esc(review.get('fingerprint', {}).get('framework_fixed'))}｜规则来源={esc(review.get('fingerprint', {}).get('rule_source'))}｜生成={esc(review.get('generated_at'))}</div>
    </header>
    <section class="grid">
      {cards}
    </section>
    <section class="scales">
      {panels}
    </section>
  </main>
</body>
</html>
"""


def latest_review_path() -> Path | None:
    files = sorted((ROOT / "data" / "pdca").glob("pdca_review_*.json"))
    return files[-1] if files else None


def main() -> int:
    parser = argparse.ArgumentParser(description="Render PDCA review dashboard")
    parser.add_argument("--date", default=None)
    args = parser.parse_args()
    if args.date:
        review_path = ROOT / "data" / "pdca" / f"pdca_review_{args.date}.json"
    else:
        review_path = latest_review_path()
    if review_path is None or not review_path.exists():
        print("需先生成PDCA复盘JSON")
        return 2
    review = read_json(review_path)
    html_text = build_html(review)
    output = ROOT / "00_请先看这里" / "PDCA复盘看板.html"
    output.write_text(html_text, encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
