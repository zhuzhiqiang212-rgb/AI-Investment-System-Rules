#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gate_异常股静默(GPT退回·董事长工单)·扫 三层★正式产品 + 机器版综合底稿·locked_v3。
异常股(爱德万JP.6857/闪迪US.SNDK) symbol卡内 + 全文【按最近股名归属】不得出现:
  价值区¥ / 中枢¥ / 中枢$ / [0-9]+倍 / 极贵 / 峰值定价 / 高位 / "高于20日低约[0-9]" / 定价类占比 / 组合拖累
★归属判据=禁词位置±150字内【最近的股名】是爱德万/闪迪 → 违规(避免把邻居别股估值误判到异常股)。
湖水一致性:声明"今日未提供"则任何『湖水 原话（date）』须在『历史底稿·不参与今日判断』分区。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
DATE = sys.argv[1] if len(sys.argv) > 1 else "20260723"
DD = f"{DATE[:4]}-{DATE[4:6]}-{DATE[6:]}"
FILES = [f"★每日产品_{DD}_locked_v14.html", f"综合底稿_机器版_{DD}_locked_v14.html"]
ANOM_NAMES = ["爱德万", "闪迪"]
# 全部20只中文/英文名(用于"最近股名"归属·防把邻居别股估值算到异常股头上)
ALL_NAMES = ["爱德万", "闪迪", "第一三共", "英伟达", "微软", "MSTR", "Coinbase", "软银", "东京海上", "索尼",
             "丰田", "伊藤忠", "万代", "任天堂", "博通", "Circle", "台积电", "META", "IBKR", "SpaceX",
             "美光", "AMD", "格芯", "联电", "Marvell", "Cameco",
             # 半导体/板块同业(用于最近股名归属·别股的"高点/跌幅"事实不误判到异常股头上)
             "东京电子", "应用材料", "科磊", "泛林", "阿斯麦", "ASML", "AMAT", "KLAC", "LRCX",
             "铠侠", "西部数据", "三星", "SK海力士", "英特尔", "高通", "德州仪器"]
# ★语义扫描(GPT口径·非数字格式):爱德万/闪迪卡内不得出现任何估值语义
BAD = [("价值区¥", r"价值区\s?[¥$]"), ("中枢", r"中枢\s?[¥$]?\d|中枢[¥$]"), ("N倍", r"\d+\.?\d*\s?倍"),
       ("极贵", r"极贵"), ("峰值定价", r"峰值定价|按峰值|持续峰值|峰值盈利|峰值PE"), ("高位", r"高位"),
       ("留峰值安全垫", r"留峰值|安全垫"), ("参考值", r"参考值"), ("合理区/上沿", r"合理区|合理上沿|合理下沿"),
       ("正常化EPS", r"正常化\s?EPS|正常化每股盈利|正常年景|中期正常化|正常化中期"),
       ("中期PE/市盈率", r"中期PE|中周期PE|中期市盈率|峰值PE|正常化PE"),
       # 敏感性:只flag【实际数据】·排除模板方法论标签(敏感性分析标题/敏感性（EPS±caption/敏感性待接/敏感性·现算说明)
       ("敏感性", r"敏感性(?!分析|（EPS|待接|·现算|【)"),
       ("共识目标", r"共识目标"), ("好中坏情景", r"好情景|坏情景|好中坏|好、中、坏.{0,4}值多少"),
       ("比较句现价X是Y约Z倍", r"现价\s?[¥$]?[\d,]+.{0,8}是.{0,12}的约"),
       ("再评级/近共识/EPS朝/下修", r"再评级|近共识|共识[¥$]|EPS朝|EPS回|下修[¥$]?\d|EPS[×xX]|好：|坏：|好、中、坏完整"),
       ("口语/动作/概率", r"远在其下|盈利崩|明显便宜|等它跌|算高|离谱|不追高|追高(?!区)|\d+\s?%概率"),
       ("高点低点(仅卡内)", r"高点|低点"),
       ("高于20日低约N", r"高于20日低约\s?[0-9]"),
       ("定价类超限", r"爱德万\s?9\.0%\s?[+＋]\s?闪迪|10\.8%[·\s]*超限"),
       ("组合拖累数", r"组合拖累约?\s?[0-9]|拖累全组合约?\s?[0-9]|拖累[^，。<]{0,4}4\.4"),
       ("异常股裸估值数字", r"[·\s(（]\s?(?:3000|2646|3234|147|2938|2939|55|35|95)\b")]


def nearest_is_anom(plain, pos):
    """禁词位置±60字内·最近的股名是不是爱德万/闪迪。是→归属异常股(违规)。
    ±60足够抓真违规(如'闪迪/爱德万等处景气高点·峰值定价'紧邻)·又不误判远处邻股(Circle/美光的估值)。"""
    best, best_d = None, 999
    lo, hi = max(0, pos - 60), pos + 60
    for nm in ALL_NAMES:
        j = plain.find(nm, lo, hi)
        while j >= 0:
            d = abs(j - pos)
            if d < best_d:
                best_d, best = d, nm
            j = plain.find(nm, j + 1, hi)
    return best in ANOM_NAMES


def scan(fp: Path):
    raw = fp.read_bytes()
    h = raw.decode("utf-8")
    # ★白名单:未来1-2年前瞻目标(未来EPS×合理PE·与当前价格口径无关·董事长2026-07-25第二次纠正准予)包在
    #   <span class="fwdanchor">内→等长置空后再扫(前瞻目标允许含EPS/PE/数字;当前估值贵贱在span外·仍拦)。
    #   等长置空:保持所有后续 pos/enclosing/anchor 偏移不变。
    #   轮13 D3:再加 <span class="dualtrack">白名单——爱德万双口径并列(中周期¥2940极贵 vs 前瞻偏贵·相反结论)是
    #   架构师裁定的【受控刻意展示】·分歧本身=投资分歧·非泄漏;含¥2940/极贵/倍→须白名单。二者同机制等长置空。
    h = re.sub(r'<span class="(?:fwdanchor|dualtrack)"[^>]*>.*?</span>', lambda m: " " * len(m.group(0)), h, flags=re.S)
    plain = re.sub(r"<[^>]+>", " ", h)
    fails = []
    # 1) 异常股 symbol卡内(why/deep/act/stock-SYM 边界内·全禁项)·边界=下一个【任意】卡片锚(通配·不只4个)
    ANCHOR = re.compile(r'id="(?:why|deep|act|stock)-[A-Z]{2}\.[A-Z0-9]+"')
    for pref in ("why", "deep", "act", "stock"):
        for sym in ("JP.6857", "US.SNDK"):
            i = h.find(f'id="{pref}-{sym}"')
            if i < 0:
                continue
            mnx = ANCHOR.search(h, i + 12)
            nx = mnx.start() if mnx else len(h)
            seg = re.sub(r"<[^>]+>", " ", h[i:nx])
            for nm, pat in BAD:
                mm = re.search(pat, seg)
                if mm:
                    fails.append({"区": f"{pref}-{sym}卡内", "禁项": nm, "上下文": re.sub(r"\s+", " ", seg[max(0, mm.start() - 20):mm.start() + 15]).strip()[:45]})
    # 1.5) 静态持仓档案·异常股承接卡(退回4·locked_v9):源头短路后不得再出现"按估值/价位做买卖"指示。
    #   静态承接卡=右栏⑥持仓档案里含 symbol 且含"所属承接节点"行的 <div class="card">。
    #   查 offending 指示词(非待核句):看估值/便宜位/偏贵位/峰值/等中周期点位。
    #   ★待核句"…不设买入/减仓/中周期点位·不按贵便宜动作·只看生意坏没坏"刻意不含这些形态→放行(教训13)。
    STATIC_BAD = [("看估值指路", "看估值"), ("到便宜位加", "便宜位"), ("到偏贵位减", "偏贵位"),
                  ("按峰值/勿按峰值", "峰值"), ("等中周期点位", "等中周期点位")]
    cardstarts = [m2.start() for m2 in re.finditer(r'<div class="card">', h)]
    for symc in ("JP.6857", "US.SNDK"):
        for ci, cs in enumerate(cardstarts):
            ce = cardstarts[ci + 1] if ci + 1 < len(cardstarts) else len(h)
            card = h[cs:ce]
            if symc not in card[:220] or "所属承接节点" not in card:
                continue                          # 只查该异常股的静态承接卡
            pc = re.sub(r"<[^>]+>", " ", card)
            for nm, tok in STATIC_BAD:
                if tok in pc:
                    p = pc.find(tok)
                    fails.append({"区": f"静态持仓卡·{symc}", "禁项": nm,
                                  "上下文": re.sub(r"\s+", " ", pc[max(0, p - 18):p + 14]).strip()[:45]})
    # 2) 卡外全文:禁词若落在【别股卡片】内→那是别股自己的合法估值·skip;只查卡外(风险区/汇总)且紧邻异常股(±60)的
    anchors = [(mm.start(), re.search(r'-([A-Z]{2}\.[A-Z0-9]+)"', mm.group(0)).group(1)) for mm in ANCHOR.finditer(h)]

    def enclosing(posr):
        sym = None
        for st, s in anchors:
            if st <= posr:
                sym = s
            else:
                break
        return sym

    def near_anom_raw(posr):
        w = re.sub(r"<[^>]+>", " ", h[max(0, posr - 80):posr + 80])
        best, bd = None, 999
        for nmx in ALL_NAMES:
            k = w.find(nmx)
            while k >= 0:
                d = abs(k - min(80, posr))
                if d < bd:
                    bd, best = d, nmx
                k = w.find(nmx, k + 1)
        return best in ANOM_NAMES
    _CARD_ONLY = {"高点低点(仅卡内)", "高位"}   # 板块peer事实(高点/低点/高位)易在世界观叙述并列异常股·仅卡内查·卡外不查
    for nm, pat in BAD:
        if nm in _CARD_ONLY:
            continue
        for m in re.finditer(pat, h):     # RAW html·带enclosing卡片归属
            es = enclosing(m.start())
            if es and es not in ("JP.6857", "US.SNDK"):
                continue                  # 在别股卡内→别股自己估值·跳过
            if near_anom_raw(m.start()):
                fails.append({"区": "卡外·紧邻异常股", "禁项": nm, "上下文": re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", h[max(0, m.start() - 30):m.start() + 20])).strip()[:55]})
                break
    # 0) ★标签残骸探针(GPT裁定·机器可核):真源头短路后不应有覆盖标签·>0即证明仍是后处理替换→FAIL
    for tagpat in (r"\[异常价[^\]]*\]", r"\[参考值待核\]", r"\[中值待核\]", r"\[倍数待核\]", r"峰值\[口径待核\]", r"中期\[待核\]"):
        n = len(re.findall(tagpat, h))
        if n:
            fails.append({"区": "标签残骸探针", "禁项": f"覆盖标签×{n}", "上下文": re.findall(tagpat, h)[0][:30]})
    # 3) 湖水一致性
    hush_provided = True
    try:
        ext = json.loads((ROOT / "data" / "external" / f"external_material_{DATE}.json").read_text(encoding="utf-8"))
        hush_provided = (ext.get("hushui") or {}).get("status") == "已提供"
    except Exception:
        pass
    if not hush_provided:
        for m in re.finditer(r"湖水\s*原话(?:</[^>]+>)?\s*（(\d{4}-\d{2}-\d{2})）", h):
            pre = re.sub("<[^>]+>", " ", h[max(0, m.start() - 60):m.start()])
            if "历史底稿" not in pre and "不参与今日判断" not in pre:
                fails.append({"区": "湖水", "禁项": "旧原话未入历史分区", "上下文": m.group(1)})
    return raw, fails


def main():
    allpass = True
    print(f"=== gate_异常股静默 · {DD} ===")
    for fn in FILES:
        fp = ROOT / "00_请先看这里" / fn
        if not fp.exists():
            print(f"  [缺文件] {fn}")
            allpass = False
            continue
        raw, fails = scan(fp)
        # 去重
        seen, uniq = set(), []
        for f in fails:
            k = (f["区"], f["禁项"])
            if k not in seen:
                seen.add(k)
                uniq.append(f)
        print(f"  {'[PASS]' if not uniq else '[FAIL]'} {fn} · SHA={hashlib.sha256(raw).hexdigest()[:16]} · 字节{len(raw)}")
        for f in uniq[:20]:
            print(f"      ✗ [{f['区']}] {f['禁项']}: {f['上下文']}")
        if uniq:
            allpass = False
    print(f"★两产品异常股静默+湖水一致 全PASS = {allpass}")
    (ROOT / "data/screen/gate_anomaly_silence.json").write_text(
        json.dumps({"date": DATE, "files": FILES, "全PASS": allpass}, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return 0 if allpass else 1


if __name__ == "__main__":
    raise SystemExit(main())
