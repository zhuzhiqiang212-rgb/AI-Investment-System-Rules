from __future__ import annotations

import html
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _pick(node: dict[str, Any], key: str) -> str:
    """取字段，缺就填‘—’。"""
    value = node.get(key) if isinstance(node, dict) else None
    if value is None or str(value).strip() == "":
        return "—"
    return str(value)


def judgment_card(date: str) -> str:
    """读判断包 data/judgment/judgment_worldview_{date}.json，
    渲染成左栏①世界观·今日判断卡；文件不存在则优雅跳过返回空串。
    display-only：只显示已有判断结论，不改动任何确定性/打分逻辑。
    """
    path = ROOT / "data" / "judgment" / f"judgment_worldview_{date}.json"
    if not path.exists():
        return ""

    data = read_json(path)
    event_node = data.get("今日事件定性", {}) or {}
    decision_node = data.get("决策合理性把关", {}) or {}
    score_node = data.get("证据链求证打分", {}) or {}

    event = _pick(event_node, "事件")
    verdict = _pick(event_node, "定性")
    pillar = _pick(event_node, "对应支柱")
    direction = _pick(decision_node, "方向")
    ring0 = score_node.get("第0环_世界是否真变") if isinstance(score_node, dict) else None

    # 徽章/边框判定色：支持=绿(dc-good)、证伪=红(dc-bad)、其它/中性=灰(dc-soft)
    verdict_stripped = verdict.strip()
    if verdict_stripped == "支持":
        tone = "dc-good"
    elif verdict_stripped == "证伪":
        tone = "dc-bad"
    else:
        tone = "dc-soft"

    judge_val = verdict
    if ring0 is not None and str(ring0).strip() != "":
        judge_val = f"{verdict}（{ring0}）"

    return f"""
    <div class="dc-card {tone}">
      <div class="dc-top">
        <div class="dc-title">① 世界观 · 第0环今日判断</div>
        <div class="dc-badge {tone}">{esc(verdict)}</div>
      </div>
      <div class="dc-row"><span class="dc-lab">【今日事件】</span><span class="dc-val">{esc(event)}</span></div>
      <div class="dc-row"><span class="dc-lab">【对照尺】</span><span class="dc-val">{esc("世界观 · " + pillar)}</span></div>
      <div class="dc-row dc-judge"><span class="dc-lab">【判定】</span><span class="dc-val">{esc(judge_val)}</span></div>
      <div class="dc-row"><span class="dc-lab">【为什么】</span><span class="dc-val">{esc(direction)}</span></div>
      <div class="dc-mini">迷你趋势图 · 待历史序列</div>
    </div>
    """


if __name__ == "__main__":
    date_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    print(judgment_card(date_arg))
