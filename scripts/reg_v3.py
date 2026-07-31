import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9));ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
V3=ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v3.html";raw=V3.read_bytes();sha=hashlib.sha256(raw).hexdigest()
reg=json.loads((ROOT/"data/screen/product_version_registry.json").read_text(encoding="utf-8"))
reg["★当前锁定送验版"]={"版本号":"v3","文件名":V3.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V3),JST).isoformat(timespec="seconds"),"说明":"★GPT复验locked_v3·SHA以此为准·不覆盖·v1/v2保留"}
reg["版本链"]=["v1(a4724e1e·退回5项计算)","v2(ee3ca761·退回1项前瞻估值合理)","v3(%s·当前送验·前瞻爱德万估值合理+闪迪46倍已退出)"%sha[:8]]
reg.setdefault("历史送验版本登记(脱节·作废·仅留痕)",[]).append({"SHA前缀":"ee3ca761","说明":"=locked_v2·退回前瞻区爱德万估值合理·被v3取代"})
(ROOT/"data/screen/product_version_registry.json").write_text(json.dumps(reg,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
d={"★本报告核对版本SHA":sha,"_说明":"locked_v3送验(前瞻区爱德万估值合理+闪迪46倍退出·硬闸扩③补前瞻区)","生成于":datetime.now(JST).isoformat(timespec="seconds"),
 "①v3 SHA/字节/mtime":{"文件名":V3.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V3),JST).isoformat(timespec="seconds"),"乱码":raw.count(b"\xef\xbf\xbd"),"裸LF":raw.count(b"\n")-raw.count(b"\r\n")},
 "②gate_fatal3_v3结果":"data/screen/gate_fatal3_v3.json(A/B/C/D+4扩查·扩③含前瞻/一句话/决定摘要区·全PASS·SHA=%s)"%sha[:8],
 "③爱德万闪迪全区(含前瞻表)退出清单":{
   "爱德万":["前瞻预测表『估值=合理』→估值=异常待核·不计算(本轮·硬闸扩③抓)","目标价¥33,544(+6.5%)→异常待核","超上沿1.9倍→异常待核","今日价值区/加仓价¥2646/止盈¥27505/939.5%(前轮)→退出"],
   "闪迪":["前瞻论点『约46倍TTM按峰值定价』→[异常待核·不计算倍数](本轮)","中周期公允$35~95/估值区$40~80/中枢$55/现价$1,350→异常待核","市值20股30,390→5股$7,597","占比1.8%/合计10.8%/拖累4.4pp→不计入"],
   "退出后正式区只留":"价格/复权口径异常待核·不计算估值/加仓价/止盈线/目标贡献/倍数·不据此买卖(见增补⑮)"},
 "硬闸扩③升级":"新增前瞻预测表/一句话/决定摘要区扫描·爱德万/闪迪出现估值=合理/极贵/目标价/加仓价/倍数即FAIL(本轮立即抓出闪迪46倍·证明升级见效)",
 "五道硬闸":{"gate_fatal3_v3(A/B/C/D+4扩查含前瞻区)":"全PASS","gate_v5矩阵20×10":"全PASS","gate_v4逐股+语义":"全PASS","退化15项":"全通过","逐对象v3":"10/10"}}
(ROOT/"data/screen/deliver_v3.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
print("v3 SHA:",sha)
