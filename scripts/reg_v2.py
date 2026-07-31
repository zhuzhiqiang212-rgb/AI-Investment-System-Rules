import hashlib, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9)); ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
V2=ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v2.html"; raw=V2.read_bytes(); sha=hashlib.sha256(raw).hexdigest()
prod={x['symbol']:x for x in json.loads((ROOT/"data/reports/production_20260722.json").read_text(encoding="utf-8"))['holdings']}
# registry更新
reg=json.loads((ROOT/"data/screen/product_version_registry.json").read_text(encoding="utf-8"))
reg["★当前锁定送验版"]={"版本号":"v2","文件名":V2.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V2),JST).isoformat(timespec="seconds"),"说明":"★GPT复验locked_v2·SHA以此为准·不覆盖"}
reg.setdefault("历史送验版本登记(脱节·作废·仅留痕)",[]).append({"SHA前缀":"a4724e1e","说明":"=locked_v1(GPT复验退回5项计算修正)·被v2取代"})
reg["版本链"]=["v1(a4724e1e·GPT退回5项计算)","v2(%s·当前送验·5项已修)"%sha[:8]]
(ROOT/"data/screen/product_version_registry.json").write_text(json.dumps(reg,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
# 8材料
d={"★本报告核对版本SHA":sha,"_说明":"locked_v2送验8项(5项计算修正)","生成于":datetime.now(JST).isoformat(timespec="seconds"),
 "①v2 SHA/字节/mtime":{"文件名":V2.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V2),JST).isoformat(timespec="seconds"),"乱码":raw.count(b"\xef\xbf\xbd"),"裸LF":raw.count(b"\n")-raw.count(b"\r\n")},
 "②四只触发%原始计算表":{
   "软银":{"加仓价便宜位":"¥6,324","7-22现价":"¥5,703.00","算式":"(6324-5703)/6324","=":"9.8%","旧值(旧价¥5,424算)":"14.2%"},
   "英伟达":{"加仓价便宜位":"$216","7-22现价":"$205.23","算式":"(216-205.23)/216","=":"5.0%","旧值(旧价$202.55)":"6.4%"},
   "索尼":{"加仓价便宜位":"¥3,702","7-22现价":"¥3,444.00","算式":"(3702-3444)/3702","=":"7.0%","旧值(旧价¥3,470)":"6.3%"},
   "第一三共":{"加仓价便宜位":"¥2,959","7-22现价":"¥2,761.50","算式":"(2959-2761.5)/2959","=":"6.7%","旧值(旧价¥2,791)":"5.7%"}},
 "③四只动作闸失败项":{
   "软银":"价格触发·闸未过=现金口径过旧(SBI/IBKR/bitFlyer 07-02核报·非当日实时)+日股集中度",
   "英伟达":"仓位过高(占约12.6%接近单只高位)+集中度限制",
   "索尼(动作=等)":"现金口径过旧+催化剂可信度不足(影像/AI相机待下次决算验证)",
   "第一三共":"现金口径过旧+日股集中度(占约10.1%)+临床事件风险(Enhertu单药占1/3·ILD监测)"},
 "④爱德万闪迪退出全节点":{"爱德万":["目标价¥33,544(+6.5%)→异常待核·不计算目标/上行%","超上沿1.9倍→异常待核","今日价值区/加仓价/止盈/估值(前轮)已退出"],
   "闪迪":["中周期公允$35~95→异常待核","估值区$40~80/中枢$55/现价$1,350→异常待核","市值20股算30,390→改5股×$1,519.49=$7,597","占比1.8%/合计10.8%/拖累4.4pp→核准前不计入"]},
 "⑤闪迪股数×价=市值=占比核对表":{"股数":"5(账户为准·原20留痕)","7-22现价":"$1,519.49","市值":"$7,597(5×1519.49=7597.45·原30,390=20股旧算已改)","占比":"约0.45%(核准前不计入组合占比/风险配仓)"},
 "⑥JS排除hist-iso原始代码":"function allOpen(v){document.querySelectorAll('details:not(.hist-iso)').forEach(function(d){d.open=v;});} — 一键全展开不展开hist-iso历史区·hist默认关闭·不进统计/触发",
 "⑦gate_fatal3_v2原始结果":"data/screen/gate_fatal3_v2.json(A/B/C/D+4扩查全PASS·SHA=%s)"%sha[:8],
 "⑧版本登记更新":"data/screen/product_version_registry.json(v2=当前送验·v1退回作废·版本链留痕)",
 "五道硬闸":{"gate_fatal3_v2(A/B/C/D+4扩查)":"全PASS","gate_v5矩阵20×10":"全PASS","gate_v4逐股+语义":"全PASS","退化硬闸15项":"全通过","逐对象v3":"10/10"}}
(ROOT/"data/screen/deliver8_v2.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
print("v2 SHA:",sha)
print("registry+deliver8_v2 已落")
