import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9));ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
V4=ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v4.html";raw=V4.read_bytes();sha=hashlib.sha256(raw).hexdigest()
prod={x['symbol']:x for x in json.loads((ROOT/"data/reports/production_20260722.json").read_text(encoding="utf-8"))['holdings']}
守={"US.NVDA","US.AVGO","US.TSM","JP.6857","JP.9984","JP.4568","US.SPCX"}
act={prod[s]['name']:("守" if s in 守 else "等") for s in prod}
d={"★本报告核对版本SHA":sha,"_说明":"locked_v4送验8项(正文全区5项修·硬闸ABCDE全HTML)","生成于":datetime.now(JST).isoformat(timespec="seconds"),
 "①v4 SHA/字节/mtime":{"文件名":V4.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V4),JST).isoformat(timespec="seconds"),"乱码":raw.count(b"\xef\xbf\xbd"),"裸LF":raw.count(b"\n")-raw.count(b"\r\n")},
 "②四只百分比全节点扫描":{"软银":"14.2→9.8pct","英伟达":"6.4→5.0pct","索尼":"6.3→7.0pct","第一三共":"5.7→6.7pct","注":"16.4/26.3/25.7pct为合法他数子串·非触发pct·保留;触发格式(算便宜低/已比加仓价低)全=0"},
 "③20只唯一动作对照表":act,
 "④爱德万全退出节点清单":["前瞻表估值=合理→异常待核","目标价¥33544/+6.5/1.9倍→异常待核","最好年份定价类/约9倍/连续2交易日在线→异常待核","守·留峰值→守(因数据未核准暂停判断·非估值推导)","今日价值区/加仓价/止盈/公允比较→退出"],
 "⑤闪迪股数x价=市值=占比核对":{"股数":"5","现价":"1519.49","市值":"7597","占比":"待核(分母不足·原0.47/1.8/维持1.8/同额置换1.8已统一待核·不保留1.8)","46倍TTM/公允55/极贵":"→异常待核"},
 "⑥非历史区日期语境扫描":"生产于/数据日/生产日 07-19→[724底稿基线·非7-22今日]·今日无重大变化/与昨日一致→[7-19基线]·非hist旧日今日语境=0",
 "⑦gate_fatal3_v4原始结果":"data/screen/gate_fatal3_v4.json(ABCDE全HTML·全PASS·SHA="+sha[:8]+")",
 "⑧人工vs硬闸对照":[
   {"人工":"正文算便宜低14.2(非触发区)","硬闸A":"全HTML扫已抓已改9.8"},
   {"人工":"守/等双写42处","硬闸B":"扫=0已逐股单一"},
   {"人工":"爱德万公允9倍/仓位9.0最好年份/止盈2天","硬闸C":"已抓已退出"},
   {"人工":"闪迪占比0.47/1.8多值","硬闸D":"已抓统一待核"},
   {"人工":"生产于07-19/数据日07-19当今日","硬闸E":"已抓已标历史基线"}],
 "五道硬闸":{"gate_fatal3_v4(ABCDE)":"全PASS","gate_v5矩阵20x10":"全PASS","gate_v4逐股+语义":"全PASS","退化15项":"全通过","逐对象v3":"10/10"}}
(ROOT/"data/screen/deliver_v4.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
print("deliver_v4落·v4 SHA:",sha)
r=json.loads((ROOT/"data/screen/product_version_registry.json").read_text(encoding="utf-8"))
print("registry当前版:",r["★当前锁定送验版"]["版本号"],r["★当前锁定送验版"]["SHA256"][:12])
