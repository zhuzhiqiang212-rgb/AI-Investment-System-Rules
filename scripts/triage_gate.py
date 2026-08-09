# -*- coding: utf-8 -*-
"""★★★轮200 · A/B/C 不可绕过的机器分档闸(GPT V7 退回·证明7:A/B/C不能在缺必要证据时越档)。
判据全靠结构化字段(§5.4)·不看自由文本:
  · 档=A 需:主要上涨依赖(非空) + 驱动证据(非空list·且经 dup_count_gate 通过·无重复计数) → 否则【强制降C】并记越档。
  · 档=B 需:查过的检索证据(非空·GPT明确『缺查过留痕→视为C』) → 否则【强制降C】并记越档。
  · 档=C 无门槛(证据不足观察池)。
★不可绕过:只认结构化字段·自报『我是A』但没证据→机器直接降C·并把越档记进 FAIL 列表。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dup_count_gate as dg


def _nonempty(x):
    if x is None:
        return False
    if isinstance(x, (list, dict, str)):
        return len(x) > 0
    return True


# ★A-1 A档:区别【可信上涨驱动】与【公司介绍/常识】——机器判据(不靠人写一句话)。
#   可信驱动须:①有量化变化{指标+幅度+期间} ②明确『未被一致预期反映』(已反映=公开信息=不算超额驱动)。
#   公司介绍(如『Axcelis做离子注入』)=静态业务描述·无量化变化·无时间→不可进A。
_B_TRACE_FIELDS = ["检索范围", "来源", "时间", "反证"]        # ★A-1 B档四项须真实存在
_C_GOV_FIELDS = ["缺少什么证据", "需要哪个数据源", "首次进入日期", "最后检查日期", "新事件触发条件", "队列老化状态"]


import re as _re
REF_DATE = "2026-08-05"   # 合理时间窗上界(当日)


def _valid_date(s, lo="2000-01-01", hi=REF_DATE):
    """合法【日历】日期(datetime真解析·拦2026-02-30这类) 且 在合理时间窗内(不能1900/未来)。"""
    import datetime as _dt
    try:
        d = _dt.datetime.strptime(str(s or ""), "%Y-%m-%d").date()
    except Exception:
        return False
    return _dt.date.fromisoformat(lo) <= d <= _dt.date.fromisoformat(hi)


import verifier

# ★★★轮203:删除所有【自报式验证标志】。以下字段名一律【不被读取】(结构性禁止提交者自证):
_BANNED_SELF_REPORT = ["已联网核验", "来源已确认", "已核实", "已验证", "我验过了", "verified", "confirmed"]


def _looks_like_text(s):
    """★轮203:【格式】检查——像不像词汇(非纯符号/非随机/非全同字符)。★这是格式·不是"有意义"(语义离线验不了)。"""
    t = str(s or "").strip()
    if len(t) < 2 or len(set(t)) <= 1:
        return False
    return bool(_re.search(r"[一-鿿]", t) or _re.search(r"[A-Za-z]{2,}", t))


def _c_format_check(gov):
    """★轮203 C-2:C档只做【格式检查】(六项齐+日期合法+像词汇)·★★★内容有效性永远=『未验证』(离线验不了意义)。
    返回 (格式通过:bool, 格式问题:list)。★绝不返回"合格"(合格暗示内容有效·会给『abc def』一个假标签)。"""
    if not isinstance(gov, dict):
        return False, ["非dict"]
    bad = [f for f in _C_GOV_FIELDS if not _nonempty(gov.get(f))]
    for df in ["首次进入日期", "最后检查日期"]:
        if _nonempty(gov.get(df)) and not _valid_date(gov.get(df)):
            bad.append(df + "(非法日期)")
    for tf in ["缺少什么证据", "需要哪个数据源", "新事件触发条件"]:
        if _nonempty(gov.get(tf)) and not _looks_like_text(gov.get(tf)):
            bad.append(tf + "(纯符号/随机·格式不像词汇)")
    return (len(bad) == 0), bad


def enforce(records):
    """★★★轮203 根治『自报字段=漏洞』:
    ①【删所有自报验证标志】——记录里任何『已联网核验/已核实/verified』字段一律【不读取】(结构性禁止)。
    ②A/B档【不可用 NOT_AVAILABLE】——A需外部来源可核·B需检索证据可核·两者都需【联网验证器】;验证器未实现(verifier.AVAILABLE=False)
      → A/B档不开放。申报A/B → 判定档=C·标 档不可用(非"可自报进入")。这正是 A=0/B=0/C=30 的结构性原因。
    ③C档只做【格式检查】·内容有效性=『未验证』(离线验不了意义)·★绝不输出"C档合格"(会给abc def假标签)。"""
    ab_available = verifier.is_available()
    out = []
    for r in records:
        code = r.get("代码"); decl = r.get("档")
        # ★结构性:剔除记录里任何自报验证标志(不读取)
        自报标志 = [k for k in _BANNED_SELF_REPORT if isinstance(r, dict) and (k in r or k in (r.get("查过的检索证据") or {}))]
        final = "C"; 越档 = False; reason = ""; 明细 = {}
        if decl in ("A", "B"):
            if not ab_available:
                越档 = True
                reason = "%s档【不可用NOT_AVAILABLE】:验证器未实现→不开放(结构性)" % decl
                明细 = {"档不可用": True, "缺": "联网验证器", "自报标志已忽略": 自报标志}
            else:
                # ★★★轮204:A/B档凭【验证器台账】开放(不读自报·只查verifier.lookup的合格记录)。
                verified = False; vdetail = None
                if decl == "A":
                    for e in (r.get("驱动证据") or []):
                        src = e.get("外部来源") or {}
                        # ★轮205:按【五元组】查台账(六项对齐核过的才合格·防跨事实错配)
                        led = verifier.lookup(src.get("可核链接或文件"), e.get("五元组"))
                        if led and led.get("合格") is True:
                            verified = True; vdetail = led; break
                else:  # B
                    tr = r.get("查过的检索证据") or {}
                    led = verifier.lookup(tr.get("来源"), tr.get("五元组"))
                    if led and led.get("合格") is True:
                        verified = True; vdetail = led
                if verified:
                    final = decl
                    明细 = {"验证器台账合格": True, "台账记录": vdetail, "自报标志已忽略": 自报标志}
                else:
                    越档 = True
                    reason = "%s档:外部来源【未经验证器核验/或核验不合格】→不开放(自报标志被忽略)" % decl
                    明细 = {"验证器台账合格": False, "自报标志已忽略": 自报标志}
        else:
            final = "C"
            if decl not in ("C", None):
                越档 = True; reason = "未知档位『%s』→按C处理" % decl
        # ★C档:格式检查 + 内容有效性未验证(永不"合格")
        if final == "C":
            fmt_ok, fmt_bad = _c_format_check(r.get("C档治理"))
            明细["C档格式检查"] = ("通过" if fmt_ok else "不通过")
            明细["C档格式问题"] = fmt_bad
            明细["C档内容有效性"] = "未验证(离线无法验证语义·须人工/联网核)"
        out.append({"代码": code, "申报档": decl, "判定档": final, "越档": 越档,
                    "C档格式检查": 明细.get("C档格式检查"), "C档内容有效性": 明细.get("C档内容有效性"),
                    "原因": reason, "明细": 明细})
    格式不通过 = [x for x in out if x["判定档"] == "C" and x.get("C档格式检查") == "不通过"]
    return {
        "逐只": out,
        "有越档": any(x["越档"] for x in out),
        "越档清单": [x for x in out if x["越档"]],
        "A_B档状态": ("可用" if ab_available else "★不可用NOT_AVAILABLE(无联网验证器)"),
        "C档格式不通过清单": [x["代码"] for x in 格式不通过],
        "★C档结论": "格式检查见逐只·★★★内容有效性一律=未验证(离线只能做格式检查·不主张内容合格)",
        "各档最终数量": {g: sum(1 for x in out if x["判定档"] == g) for g in ("A", "B", "C")},
        "★总闸": ("A/B档不可用(无验证器)·C档仅格式检查" if not ab_available else "验证器可用"),
        "★说明": "轮203:删自报验证标志(不读取);A/B需联网验证器·未实现→NOT_AVAILABLE不开放(A=0/B=0结构性);C档只格式检查·内容未验证·不输出合格。",
    }


# ═══ 攻击测试(证明7):申报A/B但缺证据 → 必须被降C ═══
def _attack_A_no_evidence():
    return [{"代码": "US.FAKE_A", "档": "A", "主要上涨依赖": "AI需求", "驱动证据": []}]  # 缺驱动证据


def _attack_A_dupe_evidence():
    # 申报A·有证据但证据是重复计数(SNDK拆分)→须被闸拦→降C
    return [{"代码": "US.FAKE_A2", "档": "A", "主要上涨依赖": "NAND", "驱动证据": dg._sample_sndk_split()}]


def _attack_B_no_trace():
    return [{"代码": "US.FAKE_B", "档": "B", "查过的检索证据": None}]


def _attack_A_selfreport_verified():
    """★★★轮203核心攻击:A档带自报『已联网核验=True』+假域名。★结构性禁止读取该标志→A档不可用→C。"""
    e = dg._E("D-sr", "订单增长", "c", ["驱动:营收"], ["情景概率"])
    e["五元组"] = {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.2, "期间": "同比"}
    e["量化变化"] = {"指标": "订单", "幅度": 0.2, "期间": "Q2"}; e["已被一致预期反映"] = False
    e["外部来源"] = {"来源标识": "fake-xyz.com", "可核链接或文件": "https://fake-xyz.com/x", "发布时间": "2026-07-30", "已联网核验": True}
    return [{"代码": "US.SRV", "档": "A", "主要上涨依赖": "订单", "已联网核验": True, "驱动证据": [e]}]


def _attack_B_selfreport_verified():
    """★★★轮203核心攻击:B档带自报『已联网核验=True』+假域名。★标志不被读取→B不可用→C。"""
    return [{"代码": "US.SRB", "档": "B", "查过的检索证据": {
        "检索范围": "订单新闻", "来源": "totally-fake-xyz.com", "已联网核验": True, "时间": "2026-08-05", "反证": "无新催化"}}]


def _attack_C_no_gov():
    """C档六项治理全缺。★格式检查不通过。"""
    return [{"代码": "US.NOGOV", "档": "C"}]


def _attack_C_random():
    """★C档六项非空但内容纯符号/随机(abc def同理)。★格式检查不通过(不像词汇)·且内容有效性一律未验证。"""
    return [{"代码": "US.RAND", "档": "C", "C档治理": {
        "缺少什么证据": "@#$%^", "需要哪个数据源": "!!!", "首次进入日期": "2026-08-05",
        "最后检查日期": "2026-08-05", "新事件触发条件": "###", "队列老化状态": "新"}}]


def _attack_C_abcdef():
    """★★★轮203:GPT填『abc def』(像词汇但无意义)。★格式检查通过·但内容有效性=未验证(★不输出合格)。"""
    return [{"代码": "US.ABC", "档": "C", "C档治理": {
        "缺少什么证据": "abc def", "需要哪个数据源": "foo bar", "首次进入日期": "2026-08-05",
        "最后检查日期": "2026-08-05", "新事件触发条件": "lorem ipsum", "队列老化状态": "新"}}]


def _legit_C():
    return [{"代码": "US.OKC", "档": "C", "C档治理": {
        "缺少什么证据": "驱动信息", "需要哪个数据源": "新闻流+一致预期", "首次进入日期": "2026-08-05",
        "最后检查日期": "2026-08-05", "新事件触发条件": "出现订单/指引变化", "队列老化状态": "新"}}]


def selftest():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("═══ triage_gate 攻击测试(轮203·A/B不可用+C格式/内容分离+删自报标志) ═══")
    # (name, records, 期望判定档, 期望格式检查[None=不查])
    cases = [
        ("申报A无驱动→C(A不可用)", _attack_A_no_evidence(), "C", None),
        ("★★A档自报已联网核验+假域名→C(标志被忽略·A不可用)", _attack_A_selfreport_verified(), "C", None),
        ("申报B无留痕→C(B不可用)", _attack_B_no_trace(), "C", None),
        ("★★B档自报已联网核验+假域名→C(标志被忽略·B不可用)", _attack_B_selfreport_verified(), "C", None),
        ("C档六项全缺→格式不通过", _attack_C_no_gov(), "C", "不通过"),
        ("C档纯符号/随机→格式不通过", _attack_C_random(), "C", "不通过"),
        ("★★C档『abc def』→格式通过·内容未验证(不给合格)", _attack_C_abcdef(), "C", "通过"),
        ("合规C(六项齐·像词汇)→格式通过·内容未验证", _legit_C(), "C", "通过"),
    ]
    allok = True
    for name, recs, exp_final, exp_fmt in cases:
        r = enforce(recs); row = r["逐只"][0]
        ok = (row["判定档"] == exp_final)
        if exp_fmt is not None:
            ok = ok and (row.get("C档格式检查") == exp_fmt) and (row.get("C档内容有效性", "").startswith("未验证"))
        # ★轮204:A/B自报攻击→验证器台账未合格(不读自报)→越档降C
        if "自报已联网核验" in name:
            ok = ok and (row["明细"].get("验证器台账合格") is False) and (row["越档"] is True)
        allok = allok and ok
        print("%s %-46s 判定档=%s 格式=%s 内容=%s" % ("✅" if ok else "❌", name, row["判定档"],
              row.get("C档格式检查"), (row.get("C档内容有效性") or "")[:6]))
    # ★★★轮205证明:跨事实错配【不能】开放A档(example.com页面无该事实·六项不齐+来源等级低→不合格)
    W = {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.2, "期间": "同比"}
    verifier.verify_source("https://example.com/", W)   # 真发HTTP·六项对齐核·写台账(应不合格)
    e = dg._E("D-mis", "ACLS订单同比增长20%", "c", ["驱动:营收"], ["情景概率"])
    e["五元组"] = W
    e["外部来源"] = {"来源标识": "example.com", "可核链接或文件": "https://example.com/", "发布时间": "2026-07-30"}
    rmis = enforce([{"代码": "US.MIS", "档": "A", "主要上涨依赖": "订单", "驱动证据": [e]}])["逐只"][0]
    ok_mis = (rmis["判定档"] == "C")   # ★跨事实错配→A不开放
    allok = allok and ok_mis
    print("%s ★★★跨事实错配(example.com页无此事实)→A档【不开放】·判定档=%s" % ("✅" if ok_mis else "❌本轮白做", rmis["判定档"]))
    st = enforce(_attack_A_selfreport_verified())["A_B档状态"]
    print("A/B档状态：%s · 验证器：%s" % (st, verifier.status()["版本"]))
    print("═══ %s ═══" % ("★全过(自报标志忽略·跨事实错配不开放A·abc def不获合格·证书正常)" if allok else "★有未达预期"))
    return 0 if allok else 1


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--records"); a = ap.parse_args()
    if a.records:
        recs = json.loads(Path(a.records).read_text(encoding="utf-8"))
        print(json.dumps(enforce(recs), ensure_ascii=False, indent=2)); return 0
    return selftest()


if __name__ == "__main__":
    raise SystemExit(main())
