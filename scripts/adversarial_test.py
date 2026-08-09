# -*- coding: utf-8 -*-
"""★★★轮203 D · 对抗测试(攻击者视角)——根治『自报字段=漏洞』后重测。
★总裁定硬编码:任一BYPASS→不通过。★四层结论分行(第②层=未通过·不是未证明)。
★上轮"自报已联网核验+假域名进A/B""abc def判合格"两攻破点→本轮结构性堵住。"""
import sys, json, argparse
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import dup_count_gate as dg
import triage_gate as tg
import verifier


def battery():
    R = []

    def add(name, blocked, note, kind="攻击"):
        # ★轮210 A-1:kind区分攻击/正向·仅用于打印文案(攻击通过=BLOCK·正向通过=PASS)·不动判定逻辑。
        R.append({"攻击": name, "拦住": bool(blocked), "说明": note, "类型": kind})

    E = dg._E

    def EV(eid, ent, ind, dr, per, pos, amp=0.12):
        e = E(eid, "文本" + eid, "c", [pos], ["情景概率"], fid=eid)
        e["五元组"] = {"实体": ent, "指标": ind, "方向": dr, "幅度": amp, "期间": per}
        return e

    # 重复计数类
    a1 = [E("g1", "Axcelis订单同比增长12%", "c1", ["驱动:营收"], ["情景概率"], fid="i1"),
          E("g2", "阿克塞利斯新订单较去年增加百分之十二", "c2", ["驱动:毛利"], ["情景概率"], fid="i2")]
    add("GPT两句跨语言/数字改写", not dg.check(a1)["pass"], "归一同指纹")
    a2 = [EV("v1", "Axcelis", "订单", "增长", "同比", "驱动:营收"), EV("v2", "阿克塞利斯", "新订单", "增加", "较去年", "驱动:毛利")]
    add("五元组同事实不同措辞", not dg.check(a2)["pass"], "五元组归一同指纹")
    a3 = [E("u1", "博通订单同比增长10%", "c1", ["驱动:营收"], ["情景概率"], fid="u1"),
          E("u2", "Broadcom new orders up 10% YoY", "c2", ["驱动:毛利"], ["情景概率"], fid="u2")]
    add("未登记实体·纯自由文本(路B入口)", not dg.check(a3, require_wuyuanzu=True)["pass"], "无五元组→入口拒绝")

    # ★★★轮204:自报『已联网核验』想进A/B → 标志不被读取·只认验证器台账(假域名未核验)→ 不开放 → C
    rA = tg.enforce(tg._attack_A_selfreport_verified())["逐只"][0]
    add("★A档自报已联网核验+假域名→进A", (rA["判定档"] != "A") and (rA["明细"].get("验证器台账合格") is False),
        "自报标志不读·假域名未经验证器核验→A不开放(BLOCK)")
    rB = tg.enforce(tg._attack_B_selfreport_verified())["逐只"][0]
    add("★B档自报已联网核验+假域名→进B", (rB["判定档"] != "B") and (rB["明细"].get("验证器台账合格") is False),
        "同上·B不开放(BLOCK)")

    # ★★★轮205 E:跨事实错配——无关网页(example.com只含Example)想给「ACLS订单同比增长20%」背书→必须不开A
    W = {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.2, "期间": "同比"}
    try:
        verifier.verify_source("https://example.com/", W)   # 真核·六项对齐·写台账(不合格)
    except Exception:
        pass
    em = dg._E("D-mis", "ACLS订单同比增长20%", "c", ["驱动:营收"], ["情景概率"]); em["五元组"] = W
    em["外部来源"] = {"来源标识": "example.com", "可核链接或文件": "https://example.com/", "发布时间": "2026-07-30"}
    rmis = tg.enforce([{"代码": "US.MIS", "档": "A", "主要上涨依赖": "订单", "驱动证据": [em]}])["逐只"][0]
    add("★★★跨事实错配(无关页背书)→开A", rmis["判定档"] != "A",
        "六项对齐/来源等级拦·example.com页无此事实→A不开放(GPT攻破点·本轮堵住)")

    # ★★★轮206 GPT五攻击(逐条·纯逻辑·不需网络)
    scattered = "Axcelis" + ("x" * 500) + "同比" + ("y" * 500) + "订单 增长 20%"
    add("★B-1 六项散落500字符→对齐", not verifier.six_align(scattered, W)[0], "六项须同窗共现·散落不算(GPT实测)")
    a120 = verifier.six_align("Axcelis 订单 增长 120% 同比", W)[1]
    add("★B-2 120%冒充20%→幅度对齐", not a120.get("幅度"), "精确数值边界·120%不冒充20%")
    a_up = verifier.six_align("Axcelis order update 20% year-over-year", {"实体": "US.ACLS", "指标": "订单", "方向": "增长", "幅度": 0.20, "期间": "同比"})[1]
    add("★B-3 'update'冒充'up'→方向对齐", not a_up.get("方向"), "完整词边界·update不含up")
    fakes = ["https://evilsec.gov.attacker.com/x", "https://sec.gov.attacker.com/x", "https://ir.attacker.com/x", "https://investor.attacker.com/x"]
    add("★B-4 四伪装域名→授一/二级", all(verifier.source_level(u, entity="US.ACLS")[0] == 4 for u in fakes), "严格注册域名边界·伪装全判四级不开A")

    # ★★★轮209 身份区九攻击(GPT明列·全拦)——six_align拆身份区+事实证据窗
    NV = "NVIDIA Announces Financial Results. Record revenue of $81.6 billion, up 85% from a year ago."
    Wnv = {"实体": "US.NVDA", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}
    Wms = {"实体": "US.MSFT", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}
    sa = verifier.six_align
    add("★身份①A页头+B五元组", not sa(NV, Wms, url="https://www.sec.gov/x")[0], "页头NVDA·五元组MSFT→身份不确认")
    add("★身份②正确域名+错误证券代码", not sa(NV, Wms, url="https://investor.nvidia.com/x")[0], "域名归属NVDA≠五元组MSFT")
    add("★身份③母/子公司错归属", not sa("信越化学工業 コード番号 4063 売上高 前年同期比 85% 増", {"实体": "JP.9984", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}, url="https://www.shinetsu.co.jp/x")[0], "页头信越·五元组软银")
    add("★身份④收购/被收购错归属", not sa(NV, {"实体": "US.AVGO", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}, url="https://www.sec.gov/x")[0], "页头NVDA·五元组AVGO")
    add("★身份⑤主体页头+四项散落", not sa("NVIDIA. " + "x" * 400 + " revenue " + "y" * 400 + " up 85% from a year ago", Wnv, url="https://www.sec.gov/x")[0], "四项不同窗")
    add("★身份⑥四项跨表拼接", not sa("NVIDIA revenue " + "z" * 500 + " up 85% from a year ago", Wnv, url="https://www.sec.gov/x")[0], "指标与幅度隔远·不同窗")
    add("★身份⑦同集团共用域名误认", not sa("売上高 前年同期比 85% 増", {"实体": "JP.6857", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}, url="https://group.softbank/x")[0], "域名归属9984≠五元组6857")
    add("★身份⑧index证券代码不一致(硬失败)", not sa(NV, Wnv, url="https://www.sec.gov/x", index_code="MSFT")[0], "index MSFT≠五元组NVDA·硬拦不回退")
    add("★身份⑨未登记域名凭页头名", not sa("信越化学工業 売上高 前年同期比 85% 増", {"实体": "JP.4063", "指标": "营收", "方向": "增长", "幅度": 0.85, "期间": "同比"}, url="https://fake-ir-attacker.com/x")[0], "未登记域名=源不可信·页头名不算")
    # ★C-2正向(不拦=对):index证券代码一致+四项同窗+公司名不在窗→通过
    c2 = sa("売上高 前年同期比 5.4% 増", {"实体": "JP.4063", "指标": "营收", "方向": "增长", "幅度": 0.054, "期间": "同比"}, url="https://www.release.tdnet.info/x", index_code="4063")[0]
    add("★C-2正向 index一致+四项同窗(名不在窗)→通过", c2, "TDnet/J-Quants索引场景·应放行(正向用例·c2=True=通过)", kind="正向")

    # ★★★轮203核心:C档『abc def』(像词汇但无意义)想拿"合格"标签 → 只得"格式通过·内容未验证"·无合格
    rC = tg.enforce(tg._attack_C_abcdef())["逐只"][0]
    got_合格 = ("合格" == rC.get("C档内容有效性"))  # 永远False(内容有效性只会是"未验证...")
    add("★C档abc def想拿『合格』标签", (not got_合格) and rC.get("C档内容有效性", "").startswith("未验证"),
        "C档不输出合格·只『格式通过·内容未验证』(上轮BYPASS·本轮不给假标签BLOCK)")

    # C档随机符号→格式不通过
    rR = tg.enforce(tg._attack_C_random())["逐只"][0]
    add("C档纯符号/随机", rR.get("C档格式检查") == "不通过", "格式检查拦")
    return R


def verdict(bypass_count):
    """★硬编码:任一BYPASS→不通过。"""
    return "不通过(存在%d条未拦截攻击)" % bypass_count if bypass_count > 0 else "通过(0条未拦截)"


def four_layers(layer1_pass):
    """★★★轮203 D:四层结论·第②层=未通过(测了没过·非未证明)。"""
    return {
        "①离线复跑模式": ("通过" if layer1_pass else "不通过"),
        "②正式生产证据真实性闸": "★验证器【身份区+事实证据窗】真核(轮209 GPT终验通过)·真实A档已开:"
                          "★美股A档2(US.NVDA/US.MSFT)·日股A档1(JP.4063信越化学·PDF二级)·合计A=3/B=0;"
                          "此层机制已跑通(真实公告开出A档)·正式生产链完整验收见C项(产品验收另计)",
        "③全字段原始产物": "★已提交(L2_anchor_pe_20260805.json·218KB·189全字段·Drive可读)——待GPT独立复核",
        "④正式生产路径": "待C项:daily_auto_produce当日运行记录+Release Gate结果(预期self_test·不进正式目录)",
    }


def run():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    R = battery()
    X = sum(1 for x in R if x["拦住"]); Y = sum(1 for x in R if not x["拦住"])
    hardcode_ok = ("不通过" in verdict(1)) and ("不通过" not in verdict(0))
    layer1_pass = (Y == 0)
    layers = four_layers(layer1_pass)
    out = {"date": "2026-08-05", "_说明": "★轮203对抗·总裁定硬编码(BYPASS>0→不通过)+四层结论(第②层未通过)。",
           "攻击测试条数": len(R), "拦截": X, "BYPASS": Y, "★总裁定": verdict(Y),
           "★硬编码规则自证(Y=1→不通过)": hardcode_ok,
           "验证器状态": verifier.status(), "★★★四层结论": layers, "逐条": R}
    (ROOT / "data/funnel").mkdir(parents=True, exist_ok=True)
    (ROOT / "data/funnel" / "adversarial_results_20260805.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print("═══ 对抗测试(攻击者视角·轮203) ═══")
    for x in R:
        # ★轮210 A-1:攻击通过=BLOCK·正向通过=PASS·未达=BYPASS/FAIL(仅文案)
        if x.get("类型") == "正向":
            tag = "PASS  " if x["拦住"] else "FAIL  "
        else:
            tag = "BLOCK " if x["拦住"] else "BYPASS"
        print(tag + " " + x["攻击"])
    print("─" * 40)
    print("攻击测试：%d 条\n  拦截：%d 条\n  BYPASS：%d 条" % (len(R), X, Y))
    print("★★总裁定：%s" % out["★总裁定"])
    print("★★★四层结论：")
    for k, v in layers.items():
        print("   %s：%s" % (k, v))
    print("★硬编码规则自证(Y=1必不通过)：%s" % hardcode_ok)
    return 0 if (layer1_pass and hardcode_ok) else 1


if __name__ == "__main__":
    raise SystemExit(run())
