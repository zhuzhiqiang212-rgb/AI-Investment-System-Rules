import hashlib,json,os
from datetime import datetime,timezone,timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9));ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
V5=ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v5.html";raw=V5.read_bytes();sha=hashlib.sha256(raw).hexdigest()
reg=json.loads((ROOT/"data/screen/product_version_registry.json").read_text(encoding="utf-8"))
reg["★当前锁定送验版"]={"版本号":"v5","文件名":V5.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V5),JST).isoformat(timespec="seconds"),"说明":"★GPT复验locked_v5·『今天哪些数据不能依赖』区爱德万/闪迪公允倍数已删·v1-v4保留"}
reg["版本链"]=["v1(a4724e1e)","v2(ee3ca761)","v3(e8e89755)","v4(922ac6ee)","v5("+sha[:8]+"·不能依赖区爱德万/闪迪公允倍数删·硬闸C扩全HTML)"]
reg.setdefault("历史送验版本登记(脱节·作废·仅留痕)",[]).append({"SHA前缀":"922ac6ee","说明":"=locked_v4·退回硬闸C漏扫不能依赖区·被v5取代"})
(ROOT/"data/screen/product_version_registry.json").write_text(json.dumps(reg,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
d={"★本报告核对版本SHA":sha,"_说明":"locked_v5(不能依赖区爱德万/闪迪公允倍数删·硬闸C扩全HTML)","生成于":datetime.now(JST).isoformat(timespec="seconds"),
 "locked_v5":{"文件名":V5.name,"SHA256":sha,"字节":len(raw),"mtime":datetime.fromtimestamp(os.path.getmtime(V5),JST).isoformat(timespec="seconds"),"乱码":raw.count(b"\xef\xbf\xbd"),"裸LF":raw.count(b"\n")-raw.count(b"\r\n")},
 "修正":{"爱德万@『今天哪些数据不能依赖』区":"删『现价27505是中周期公允3000约9倍』→『价格/复权口径异常·待专项核准;不计算估值/倍数/加仓价/止盈/目标;守=因数据未核准暂停判断·非由估值推导』",
        "闪迪@同区":"删『现价1350.034是中周期公允55约25倍』→保留现价$1,519.49异常事实·删公允55/约25倍/中周期公允"},
 "硬闸C扩区":"gate_fatal3_v5·C规则=爱德万/闪迪±40字出现公允/倍/中周期公允→FAIL·全HTML(含v4漏的『今天哪些数据不能依赖』区)",
 "gate_fatal3_v5":"data/screen/gate_fatal3_v5.json(A/B/C扩区/D/E全PASS·SHA="+sha[:8]+")",
 "五道硬闸":{"gate_fatal3_v5(ABCDE·C扩全HTML)":"全PASS","gate_v5矩阵":"全PASS","gate_v4逐股":"全PASS","退化15项":"全通过","逐对象v3":"10/10"}}
(ROOT/"data/screen/deliver_v5.json").write_text(json.dumps(d,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
print("v5 SHA:",sha)
