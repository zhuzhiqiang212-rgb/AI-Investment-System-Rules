from __future__ import annotations

import html
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PACK_DIR = ROOT / "00_请先看这里"


def esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _ticker(symbol: Any) -> str:
    """从 symbol 取主代码：去掉 US./JP./HK./CC. 之类前缀，大写。
    如 "US.NVDA"->"NVDA"、"NVDA"->"NVDA"。"""
    text = str(symbol or "").strip()
    if "." in text:
        text = text.split(".")[-1]
    return text.upper()


def _find_pack(symbol: Any, name: Any) -> Path | None:
    """在 PACK_DIR.glob("个股判断包_*.html") 里找文件名（大写）包含 ticker 或 name 的。
    token 长度须≥2 才匹配，避免误命中。命中返回该 Path，否则 None。"""
    tokens: list[str] = []
    ticker = _ticker(symbol)
    if len(ticker) >= 2:
        tokens.append(ticker)
    name_token = str(name or "").strip().upper()
    if len(name_token) >= 2:
        tokens.append(name_token)
    if not tokens:
        return None
    for path in PACK_DIR.glob("个股判断包_*.html"):
        upper_name = path.name.upper()
        for token in tokens:
            if token in upper_name:
                return path
    return None


def has_pack(symbol: Any, name: Any) -> bool:
    return _find_pack(symbol, name) is not None


def stock_research_card(symbol: Any, name: Any) -> str:
    """命中则读 pack 文本、用 html.escape(text, quote=True) 做 srcdoc，
    返回一个默认折叠的 details.card（iframe 高度自适应）；未命中返回 ""。"""
    path = _find_pack(symbol, name)
    if path is None:
        return ""
    ticker = _ticker(symbol)
    title = f"个股深度研究 · {name}({ticker})"
    pack_text = path.read_text(encoding="utf-8")
    srcdoc = html.escape(pack_text, quote=True)
    return f"""
    <details class="card static" ontoggle="var f=this.querySelector('iframe'); if(f){{setTimeout(function(){{try{{f.style.height=f.contentWindow.document.documentElement.scrollHeight+'px';}}catch(e){{}}}},30);}}">
      <summary><span>{esc(title)}</span><b>个股研究</b></summary>
      <iframe srcdoc="{srcdoc}" style="width:100%;height:600px;border:0;background:#0e1621;" onload="try{{this.style.height=this.contentWindow.document.documentElement.scrollHeight+'px';}}catch(e){{}}"></iframe>
    </details>
    """


def stock_research_section(holdings: Any) -> str:
    """对每只 holding 调 stock_research_card，把非空的拼起来；
    若一个都没有则返回 ""。外面套标题'个股深度研究（漏斗第5关·已出）'。"""
    if not holdings:
        return ""
    cards = []
    for item in holdings:
        if not isinstance(item, dict):
            continue
        card = stock_research_card(item.get("symbol"), item.get("name"))
        if card:
            cards.append(card)
    if not cards:
        return ""
    return f"""
    <details class="card">
      <summary><span>个股深度研究（漏斗第5关·已出）</span><b>已出</b></summary>
      <p class="plain">已完成深度研究的持仓，嵌入其判断包全文；未研究的持仓在持仓表内标"待补个股研究"。</p>
      {''.join(cards)}
    </details>
    """
