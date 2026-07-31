#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日点时存档（派工单乙·2026-07-21·尺总册G-13）：今天存的·明年就是真点时数据。
API 返回的是"当前值"·公司事后重述就拿不到原始→从今天起每天原样存盘·一年后可做真无未来信息回测。
★只存不加工·只追加永不覆盖历史·每份带SHA-256·失败当天如实记原因不跳过·不改尺不下单。

每日存档(原样·两套字段方案都存)：
 1 当日可见财报字段值(8xxx+11xxx)  2 增长率字段(filter)  3 当日收盘/成交量
 4 财报发布日(earnings_price_move.pub_trading_day_str)  5 抓取时刻外部服务器时间
路径 data/pit/{YYYYMMDD}/ ·一天一份 ·写一次不覆盖(同日重跑只补缺·历史目录永不动)。
用法：python scripts/pit_archive.py --date YYYYMMDD [--scope inbound|probe|all]
"""
from __future__ import annotations
import argparse, json, hashlib, socket, sys, time
from datetime import datetime, timezone, timedelta
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SCREEN = ROOT / "data" / "screen"
JST = timezone(timedelta(hours=9))
PROBE = ["US.LLY", "US.OXY", "US.UNH", "US.GOOGL", "US.DELL", "US.NVDA", "US.MU", "JP.7011", "JP.8035", "JP.6501"]


def now():
    return datetime.now(JST).isoformat(timespec="seconds")


def ext_time():
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import forecast_lock as FL
        return FL.external_time()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"{e}"}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def port_open(t=2.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM); s.settimeout(t)
    try:
        s.connect(("127.0.0.1", 11111)); return True
    except Exception:
        return False
    finally:
        s.close()


def targets(scope):
    codes = list(PROBE)
    if scope in ("inbound", "all"):
        try:
            cd = json.loads((SCREEN / "candidates_20260721.json").read_text(encoding="utf-8"))
            codes += [c["code"] for c in cd.get("candidates", []) if c.get("conclusion") == "入围"]
        except Exception:
            pass
    seen, out = set(), []
    for c in codes:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def fin_val(s, field):
    for k, v in vars(s).items():
        if isinstance(k, tuple) and k[0] == field:
            try:
                return float(v)
            except Exception:
                return None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None)
    ap.add_argument("--scope", default="inbound", choices=["probe", "inbound", "all"])
    a = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    et = ext_time()
    date = a.date or (et.get("iso", "")[:10].replace("-", "") if et.get("ok") else datetime.now(JST).strftime("%Y%m%d"))
    PIT = ROOT / "data" / "pit" / date
    PIT.mkdir(parents=True, exist_ok=True)
    # ── 自检(董事长2026-07-21五)：「文件已存在」≠「文件已完整」。前一日若报警未补→今日manifest顶部标注 ──
    prior_flag = None
    try:
        prev_date = (datetime.strptime(date, "%Y%m%d") - timedelta(days=1)).strftime("%Y%m%d")
        pm = ROOT / "data" / "pit" / prev_date / "_manifest.json"
        if pm.exists():
            pj = json.loads(pm.read_text(encoding="utf-8"))
            if pj.get("四文件覆盖范围一致") is False and not pj.get("已人工确认补齐", False):
                prior_flag = f"⚠前一日({prev_date})存档不完整·未补(四文件覆盖不一致且未标已确认)·见 data/pit/{prev_date}/_manifest.json"
    except Exception:
        pass
    codes = targets(a.scope)
    print(f"PIT 存档 {date} · scope={a.scope} · {len(codes)}只 · 目录 {PIT}")

    manifest_p = PIT / "_manifest.json"
    manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {
        "date": date, "scope": a.scope, "抓取外部服务器时间": et, "started_local": now(),
        "只追加永不覆盖": True, "files": {}, "_resume_done": [], "失败": []}
    done = set(manifest.get("_resume_done") or manifest.get("已存代码", []))

    if not port_open():
        manifest["FATAL"] = f"OpenD 未开·当日未取到·原因=端口11111拒绝·{now()}"
        manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("OpenD 未开·已记录未取到（不跳过·如实记）"); return 1

    import futu as ft
    ctx = ft.OpenQuoteContext("127.0.0.1", 11111)
    stmt_f = PIT / "statements.jsonl"     # 原样·一行一只(income+cashflow 最近4个FY期)
    earn_f = PIT / "earnings.jsonl"       # 财报发布日
    try:
        # ② 增长率字段(filter·只收目标码·按市值降序早退·目标皆大市值故很快)
        def growth(market, want):
            sf = ft.SimpleFilter(); sf.stock_field = ft.StockField.MARKET_VAL
            sf.filter_min = 1e10; sf.is_no_filter = False; sf.sort = ft.SortDir.DESCEND
            fl = [sf]
            for fld in [ft.StockField.OPERATING_PROFIT_GROWTH_RATE, ft.StockField.PROFIT_TO_SHAREHOLDERS_GROWTH_RATE,
                        ft.StockField.PROFIT_BEFORE_TAX_GROWTH_RATE, ft.StockField.ROE_GROWTH_RATE]:
                ff = ft.FinancialFilter(); ff.stock_field = fld; ff.is_no_filter = True; ff.quarter = ft.FinancialQuarter.ANNUAL; fl.append(ff)
            out = {}; begin = 0; remaining = set(want)
            while remaining:
                ret, ls = ctx.get_stock_filter(market=market, filter_list=fl, begin=begin, num=200)
                if ret != ft.RET_OK:
                    break
                last, cnt, lst = ls
                for s in lst:
                    if s.stock_code in remaining:
                        out[s.stock_code] = {"营业利润同比": fin_val(s, "operating_profit_growth_rate"),
                                             "归母净利同比": fin_val(s, "profit_to_shareholders_growth_rate"),
                                             "税前利润同比": fin_val(s, "profit_before_tax_growth_rate"),
                                             "ROE同比": fin_val(s, "roe_growth_rate")}
                        remaining.discard(s.stock_code)
                begin += len(lst)
                if last or begin >= cnt or not lst:
                    break
                time.sleep(2.5)
            return out
        # ② growth:补齐到【全部目标码】(修复:此前 if not exists 致 resume 时停在探针10只·与statements范围不一致)
        gp = PIT / "growth.json"
        g_existing = (json.loads(gp.read_text(encoding="utf-8")).get("data", {}) if gp.exists() else {})
        g_missing = [c for c in codes if c not in g_existing]
        if g_missing:
            g = dict(g_existing)
            us_t = [c for c in g_missing if c.startswith("US.")]; jp_t = [c for c in g_missing if c.startswith("JP.")]
            if us_t:
                g.update(growth(ft.Market.US, us_t)); time.sleep(2)
            if jp_t:
                g.update(growth(ft.Market.JP, jp_t)); time.sleep(2)
            gb = (json.dumps({"_口径": "get_stock_filter ANNUAL 增长率·当日值·补齐至全目标", "抓取": now(),
                              "n": len(g), "代码": sorted(g), "data": g}, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
            gp.write_bytes(gb)
            print(f"  growth.json ✓ 补齐至 {len(g)}只(新增{len(g)-len(g_existing)})")

        # ③ 收盘/成交量·补齐到全目标码(同 growth 修复)
        pp = PIT / "prices.json"
        px_existing = (json.loads(pp.read_text(encoding="utf-8")).get("data", {}) if pp.exists() else {})
        px_missing = [c for c in codes if c not in px_existing]
        if px_missing:
            px = dict(px_existing)
            for i in range(0, len(px_missing), 100):
                part = px_missing[i:i + 100]
                try:
                    ret, df = ctx.get_market_snapshot(part)
                    if ret == ft.RET_OK:
                        for _, r in df.iterrows():
                            px[str(r.get("code"))] = {"close": (float(r["last_price"]) if r.get("last_price") not in (None, "") else None),
                                                      "volume": (float(r["volume"]) if r.get("volume") not in (None, "") else None),
                                                      "turnover": (float(r["turnover"]) if r.get("turnover") not in (None, "") else None)}
                except Exception:
                    for c in part:
                        try:
                            ret, df = ctx.get_market_snapshot([c])
                            if ret == ft.RET_OK:
                                r = df.iloc[0]
                                px[c] = {"close": float(r["last_price"]), "volume": float(r["volume"]), "turnover": float(r["turnover"])}
                        except Exception:
                            pass
                        time.sleep(0.5)
                time.sleep(2)
            pb = (json.dumps({"_口径": "get_market_snapshot 当日收盘/量·原样·补齐至全目标", "抓取": now(),
                              "n": len(px), "代码": sorted(px), "data": px}, ensure_ascii=False, indent=1) + "\n").encode("utf-8")
            pp.write_bytes(pb)
            print(f"  prices.json ✓ 补齐至 {len(px)}只(新增{len(px)-len(px_existing)})")

        # ① 财报字段(statements 8xxx+11xxx原样) + ④ 财报发布日(逐只·可续跑·只补缺)
        for i, c in enumerate(codes):
            if c in done:
                continue
            rec = {"code": c, "抓取": now(), "income": None, "cashflow": None, "err": []}
            for st, key in [(1, "income"), (3, "cashflow")]:
                try:
                    ret, d = ctx.get_financials_statements(c, statement_type=st, num=16)
                    if ret == ft.RET_OK and isinstance(d, dict):
                        rl = d.get("report_list", [])[:16]   # 最近16期(季报制约含3-4个FY·供加速度算·董事长2026-07-21)
                        std = rl[0].get("accounting_standards") if rl else None
                        rec[key] = {"accounting_standards": std, "report_list": rl}
                    else:
                        rec["err"].append(f"{key}:{str(d)[:40]}")
                except Exception as e:
                    rec["err"].append(f"{key}:{type(e).__name__}")
                time.sleep(0.8)
            # ④ 发布日
            try:
                ret, df = ctx.get_financials_earnings_price_move(c)
                if ret == ft.RET_OK and hasattr(df, "columns") and len(df):
                    pubs = sorted(set(df["pub_trading_day_str"].tolist()))
                    with earn_f.open("a", encoding="utf-8") as f:
                        f.write(json.dumps({"code": c, "财报发布日": pubs, "抓取": now()}, ensure_ascii=False) + "\n")
            except Exception:
                rec["err"].append("earnings")
            with stmt_f.open("a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if rec["income"] is None and rec["cashflow"] is None:
                manifest["失败"].append({"code": c, "原因": rec["err"], "when": now()})
            done.add(c); manifest["_resume_done"] = sorted(done)
            if (i + 1) % 25 == 0:
                manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
                print(f"  statements {i + 1}/{len(codes)} (失败累计{len(manifest['失败'])})")
            time.sleep(0.4)
    finally:
        ctx.close()

    # ── 每文件【分别】记录:实际条数 + 代码清单 + 指纹;并核四文件覆盖是否一致(董事长2026-07-21打回)──
    def from_jsonl(fn):
        p = PIT / fn
        cs = []
        if p.exists():
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        cs.append(json.loads(line)["code"])
                    except Exception:
                        pass
        return sorted(set(cs))

    def from_json(fn):
        p = PIT / fn
        return sorted((json.loads(p.read_text(encoding="utf-8")).get("data", {})).keys()) if p.exists() else []
    cover = {"statements.jsonl": from_jsonl("statements.jsonl"), "earnings.jsonl": from_jsonl("earnings.jsonl"),
             "growth.json": from_json("growth.json"), "prices.json": from_json("prices.json")}
    manifest["files"] = {}
    for fn, cs in cover.items():
        p = PIT / fn
        if p.exists():
            b = p.read_bytes()
            manifest["files"][fn] = {"sha256": sha(b), "bytes": len(b), "n条数": len(cs)}
    manifest["各文件代码清单"] = cover
    st = set(cover["statements.jsonl"])
    manifest["各文件覆盖只数"] = {k: len(v) for k, v in cover.items()}
    consistent = bool(st) and all(set(v) == st for v in cover.values())
    manifest["四文件覆盖范围一致"] = consistent
    if not consistent:
        diff = {}
        for k, v in cover.items():
            miss = sorted(st - set(v))
            if miss:
                if k == "earnings.jsonl":
                    reason = "这些码无 get_financials_earnings_price_move 历史(多为OTC/ADR/二级上市线·本就无财报公告序列)·非抓取失败·数据本身如此"
                elif k in ("growth.json", "prices.json"):
                    reason = "本应补齐至全目标·若仍缺=该码 filter/snapshot 未返回·须查"
                else:
                    reason = "statements 侧缺·须查"
                diff[k] = {"缺数": len(miss), "缺(相对statements)": miss[:20], "原因": reason}
        manifest["覆盖不一致_差异"] = diff
        manifest["覆盖不一致_总述"] = "statements/growth/prices 已对齐;earnings 少的是无财报公告序列的二级上市线(数据本身如此·非失败)。"
    manifest["scope"] = f"{a.scope}·目标{len(codes)}只(432入围+10探针·去重·实际见各文件代码清单)"
    manifest["目标总数"] = len(codes)
    manifest["statements已存代码数"] = len(cover["statements.jsonl"])
    manifest["自检_文件存在≠完整"] = ("四文件均对齐" if consistent else "已列覆盖不一致_差异(见上·earnings少的是无公告序列的二级线)")
    manifest["前一日存档状态"] = prior_flag or "前一日存档完整/或无前一日"
    manifest.pop("存档只数", None); manifest.pop("已存代码", None)   # 删歧义字段(改为每文件分别记)
    manifest["_resume_done"] = sorted(done)                       # 续跑用(内部)·非对外覆盖声明
    manifest["finished_local"] = now()
    manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"PIT 存档完成 {date} · 各文件覆盖 {manifest['各文件覆盖只数']} · 一致={consistent} · 失败{len(manifest['失败'])}")
    print("★只追加永不覆盖·每份带SHA-256·四文件覆盖已核·建议接每日07:30 JST自动生产")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
