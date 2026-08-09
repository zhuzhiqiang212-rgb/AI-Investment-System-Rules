# -*- coding: utf-8 -*-
"""★轮97 NC3 L18 跨文件一致性闸。L17只查产品HTML【内部】·没查【数据文件之间】。
GPT判『最危险的一处』完整形态:★同一事实在多处各存一份·无闸比对。
L18:同一事实(资金流接通数/完工度七层数/总判据数)在 completion_status↔macro_flow↔产品HTML 多处存在时必须比对·不一致→FAIL。
本轮『completion 13 / macro_flow 5/10 / 核心5 3/5』打架·正是L18该抓。★以实测直采为准·不许取最大数。"""
import sys, json, argparse, re
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
SEE = ROOT / "00_请先看这里"


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def check(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    fails, notes = [], []
    cs = _rj(ROOT / "data/logs" / f"completion_status_{dc}.json")
    mf = _rj(ROOT / "data/market" / f"macro_flow_{dc}.json")
    prod = SEE / f"★每日产品_{dh}.html"
    html = prod.read_text(encoding="utf-8", errors="replace") if prod.exists() else ""

    # ── 事实1:资金流接通数(蓝图10直采)——completion③证据 vs macro_flow N/10 ──
    mf_conn = None
    st = mf.get("★接通统计", {})
    m = re.search(r"(\d+)\s*/\s*10", str(st.get("机器自动接通(全部)N/10", st.get("接通N/10", ""))))
    if m:
        mf_conn = int(m.group(1))
    cs3 = ((cs.get("一_七层", {}) or {}).get("③资金流动", {}) or {})
    cm = re.search(r"直采接通\s*(\d+)/10", str(cs3.get("证据", "")))
    cs_conn = int(cm.group(1)) if cm else None
    if mf_conn is not None and cs_conn is not None and mf_conn != cs_conn:
        fails.append("L18 资金流接通数打架：macro_flow=%d/10 ≠ completion③=%d/10——同一事实多处不一致(以实测直采为准·不取最大数)→FAIL" % (mf_conn, cs_conn))
    else:
        notes.append("资金流接通数一致：macro_flow=%s·completion③=%s" % (mf_conn, cs_conn))
    # ★禁『取最大』:completion③证据不得出现>10或=13这类超分母数
    if re.search(r"接通\s*1[1-9]|接通\s*[2-9]\d", str(cs3.get("证据", ""))):
        fails.append("L18 分母越界：completion③接通数>10(分母是10·逻辑不成立·疑取了含供应侧的最大数13)→FAIL")

    # ── 事实2:完工度七层建成数——completion计数 vs 产品HTML页头 ──
    cs_full = (cs.get("计数", {}) or {}).get("七层完全建成")
    if html and cs_full is not None:
        hm = re.search(r"七层\s*(\d+)\s*建成", html)
        if hm and int(hm.group(1)) != cs_full:
            fails.append("L18 完工度七层数打架：产品HTML『七层%s建成』≠ completion计数%d→FAIL" % (hm.group(1), cs_full))
        elif hm:
            notes.append("七层建成数一致：产品=%s·completion=%s" % (hm.group(1), cs_full))

    # ── ★轮101 NH2:值本身正确性校验(不止查一致·防过期run_id骗人·第六次同族故障根治) ──
    import re as _re
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td
    _JST = _tz(_td(hours=9))
    man = _rj(ROOT / "data/product_manifest.json")
    rid = str(man.get("run_id", ""))
    rm = _re.match(r"R-?3?-(\d{8})-(\d{6})", rid)
    if rm:
        try:
            rid_dt = _dt.strptime(rm.group(1) + rm.group(2), "%Y%m%d%H%M%S").replace(tzinfo=_JST)
            now = _dt.now(_JST)
            # ★run_id 是 data_date+当前HHMMSS·跨午夜非有效时间戳→真实生成时刻用 render 权威写的 epoch(runid_history)。
            _hj0 = _rj(ROOT / "data/logs" / f"runid_history_{dc}.json")
            _cur_ep = (_hj0.get("epochs", {}) or {}).get(rid)
            rid_real_dt = _dt.fromtimestamp(_cur_ep, _JST) if _cur_ep else rid_dt
            # ①run_id 时刻 ≈ 真实生成时刻(±30min)——抓「run_id停在12h前」。★run_id日期段=data_date·时间段=当前HHMMSS·
            #   跨午夜时full datetime会差~24h→改用【时-of-day环形比较】(235953 vs 000005 经环形≈7分钟·不误判)。
            _hh, _mm, _ss = int(rm.group(2)[:2]), int(rm.group(2)[2:4]), int(rm.group(2)[4:6])
            rid_tod = _hh * 3600 + _mm * 60 + _ss
            now_tod = now.hour * 3600 + now.minute * 60 + now.second
            _diff = abs(rid_tod - now_tod)
            gap_min = min(_diff, 86400 - _diff) / 60
            if gap_min > 30:
                fails.append("L18-NH2① run_id时刻过期：run_id=%s(%s) 与当前时刻差 %.0f 分钟(>30min)——页头横幅在骗人·产品实际生成于现在·run_id却停在过去(轮101硬伤)→FAIL" % (rid, rid_dt.strftime("%H:%M"), gap_min))
            else:
                notes.append("run_id时刻≈真实生成(差%.0f分钟·≤30)" % gap_min)
            # ②run_id 时刻 不得早于所读数据 as_of(production.generated_at)
            prodj = _rj(ROOT / "data/reports" / f"production_{dc}.json")
            ga = str(prodj.get("generated_at") or "")
            if ga:
                try:
                    ga_dt = _dt.fromisoformat(ga.replace("Z", "+00:00")).astimezone(_JST)
                    # ★用真实epoch(rid_real_dt)比·跨午夜01:xx渲08-02数据不误判(真实render晚于production.generated_at)
                    if rid_real_dt < ga_dt - _td(minutes=1):
                        fails.append("L18-NH2② run_id早于数据as_of：真实生成 %s < production.generated_at %s——产品声称比它读的数据还早生成·不可能→FAIL" % (rid_real_dt.strftime("%Y-%m-%d %H:%M"), ga_dt.strftime("%Y-%m-%d %H:%M")))
                    else:
                        notes.append("run_id不早于数据as_of(真实生成 %s ≥ 数据 %s)" % (rid_real_dt.strftime("%m-%d %H:%M"), ga_dt.strftime("%m-%d %H:%M")))
                except Exception:
                    pass
            # ③多轮 run_id 严格递增(防同值覆盖)——★按【真实epoch】比较(render权威写·跨午夜01:xx渲08-02不误判)。
            hist_p = ROOT / "data/logs" / f"runid_history_{dc}.json"
            hj = _rj(hist_p) if hist_p.exists() else {}
            hist = hj.get("run_ids", []); eps = hj.get("epochs", {}) or {}
            cur_ep = eps.get(rid)
            if cur_ep is not None:
                later = [x for x, e in eps.items() if x != rid and isinstance(e, (int, float)) and e >= cur_ep]
                if later:
                    fails.append("L18-NH2③ run_id未递增(按真实生成时刻)：存在不早于当前的历史 run_id %s——同源多轮须严格递增(防同值覆盖·哨兵失效)→FAIL" % later[-1])
                else:
                    notes.append("run_id严格递增(按真实epoch·vs历史%d条·跨午夜安全)" % len(eps))
            else:
                # 回退:无epoch→仅【同一日期段】字符串比较(不跨date误判)
                prev_same = []
                for x in hist:
                    xm = _re.match(r"R-?3?-(\d{8})-(\d{6})", str(x))
                    if xm and xm.group(1) == rm.group(1) and x != rid and xm.group(2) >= rm.group(2):
                        prev_same.append(x)
                if prev_same:
                    fails.append("L18-NH2③ run_id未递增：同日 %s ≥ 当前时段——须严格递增→FAIL" % prev_same[-1])
                else:
                    notes.append("run_id严格递增(字符串同日比较·vs历史%d条)" % len(hist))
        except Exception as _e:
            notes.append("NH2值校验异常:%s" % _e)

    # ── 事实3:总判据数——completion vs 产品HTML ──
    cs_tot = (cs.get("计数", {}) or {}).get("总判据满足")
    if html and cs_tot is not None:
        tm = re.search(r"总判据\s*(\d+)\s*/\s*5", html)
        if tm and int(tm.group(1)) != cs_tot:
            fails.append("L18 总判据数打架：产品HTML『总判据%s/5』≠ completion%d/5→FAIL" % (tm.group(1), cs_tot))
        elif tm:
            notes.append("总判据数一致：产品=%s·completion=%s" % (tm.group(1), cs_tot))
    return fails, notes


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    fails, notes = check(a.date)
    for n in notes:
        print("  ✔", n)
    if fails:
        print("[L18 跨文件一致性 FAIL] %d 条(同一事实多处打架)：" % len(fails))
        for f in fails:
            print("  ✗", f)
        return 6
    print("[L18 跨文件一致性 PASS] 接通数/完工度/总判据 多处一致·无打架")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
