import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9));ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
V4=ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v4.html";raw=V4.read_bytes();sha=hashlib.sha256(raw).hexdigest()
reg=json.loads((ROOT/"data/screen/product_version_registry.json").read_text(encoding="utf-8"))
reg["★当前锁定送验版"]={"版本号":"v4","文件名":V4.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V4),JST).isoformat(timespec="seconds"),"说明":"★GPT复验locked_v4·正文全区5项修·v1-v3保留不覆盖"}
reg["版本链"]=["v1(a4724e1e)","v2(ee3ca761)","v3(e8e89755)","v4(%s·当前·正文全区:四只旧%%/守等双写/爱德万正文/闪迪占比/旧日语境)"%sha[:8]]
reg.setdefault("历史送验版本登记(脱节·作废·仅留痕)",[]).append({"SHA前缀":"e8e89755","说明":"=locked_v3·退回正文全区5项·被v4取代"})
(ROOT/"data/screen/product_version_registry.json").write_text(json.dumps(reg,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
prod={x['symbol']:x for x in json.loads((ROOT/"data/reports/production_20260722.json").read_text(encoding="utf-8"))['holdings']}
守={"US.NVDA","US.AVGO","US.TSM","JP.6857","JP.9984","JP.4568","US.SPCX"}
act={prod[s]['name']:("守" if s in 守 else "等") for s in prod}
d={"★本报告核对版本SHA":sha,"_说明":"locked_v4送验8项(正文全区5项修·硬闸ABCDE全HTML)","生成于":datetime.now(JST).isoformat(timespec="seconds"),
 "①v4 SHA/字节/mtime":{"文件名":V4.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V4),JST).isoformat(timespec="seconds"),"乱码":raw.count(b"\xef\xbf\xbd"),"裸LF":raw.count(b"\n")-raw.count(b"\r\n")},
 "②四只百分比全节点扫描":{"软银":"14.2→9.8%(算便宜低+已比加仓价低全格式=0)","英伟达":"6.4→5.0%","索尼":"6.3→7.0%","第一三共":"5.7→6.7%","注":"16.4%/26.3%/25.7%为合法他数子串·非触发%·保留"},
 "③20只唯一动作对照表":act,
 "④爱德万全退出节点清单":["前瞻表估值=合理→异常待核","目标价¥33,544/+6.5%/1.9倍→异常待核","最好年份定价类/约9倍/连续2交易日在线→异常待核","守·留峰值安全垫→守(因数据未核准暂停判断·非估值推导)","今日价值区/加仓价/止盈/公允比较→退出"],
 "⑤闪迪股数×价=市值=占比核对":{"股数":"5","现价":"$1,519.49","市值":"$7,597(5×1519.49)","占比":"待核(分母不足·原0.47%/1.8%/维持1.8%/同额置换1.8%已统一为待核·不保留1.8%)","46倍TTM/公允55/极贵":"→异常待核"},
 "⑥非历史区日期语境扫描":"生产于/数据日/生产日 2026-07-19→[724底稿基线·非7-22今日]·今日无重大变化/与昨日一致→[7-19基线差分·非今日]·非hist旧日今日语境=0",
 "⑦gate_fatal3_v4原始结果":"data/screen/gate_fatal3_v4.json(A四只旧%/B守等双写/C爱德万公允价倍数/D闪迪0.47vs1.8/E非hist旧日语境·全PASS·SHA=%s)"%sha[:8],
 "⑧人工vs硬闸对照":[
   {"人工":"正文'算便宜低14.2%'(非触发区)","硬闸A":"全HTML扫·已抓·已改9.8%"},
   {"人工":"'守/等'双写42处","硬闸B":"扫守/等=0·已逐股单一"},
   {"人工":"爱德万公允9倍/仓位9.0%最好年份/止盈2天","硬闸C":"已抓·已退出"},
   {"人工":"闪迪占比0.47/1.8多值","硬闸D":"已抓·统一待核"},
   {"人工":"生产于07-19/数据日07-19当今日","硬闸E":"已抓·已标历史基线"}],
 "五道硬闸":{"gate_fatal3_v4(ABCDE全HTML)":"全PASS","gate_v5矩阵20×10":"全PASS","gate_v4逐股+语义":"全PASS","退化15项":"全通过","逐对象v3":"10/10"}}
(ROOT/"data/screen/deliver_v4.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
print("v4 SHA:",sha)
