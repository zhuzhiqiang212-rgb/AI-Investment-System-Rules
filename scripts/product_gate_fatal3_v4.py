import hashlib,json,os,re
from datetime import datetime,timezone,timedelta
from pathlib import Path
JST=timezone(timedelta(hours=9));ROOT=Path("G:/我的云端硬盘/AI_Investment_System")
P=ROOT/"00_请先看这里"/"★每日产品_2026-07-22.html"  # 先扫工作文件·PASS后冻结v4
raw=P.read_bytes();h=raw.decode("utf-8");sha=hashlib.sha256(raw).hexdigest()
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
F={"A_四只旧%(算便宜低/已比加仓价低)":[],"B_守等双写/为什么不选矛盾":[],"C_爱德万公允价/倍数/止盈天数/目标贡献":[],"D_闪迪0.47%与1.8%并存":[],"E_非hist旧日今日昨日差分":[]}
# A 四只旧%(触发%格式·非16.4/26.3子串)
for old in ["14.2%","6.4%","6.3%","5.7%"]:
    for m in re.finditer(r"(算便宜（低 ?|已比加仓价低 ?<b>|低 ?)"+re.escape(old),h):
        if not hist(m.start()): F["A_四只旧%(算便宜低/已比加仓价低)"].append({old:pl(h[m.start()-14:m.start()+8])})
# B 守/等双写 + 为什么不选等(索尼=等)
for m in re.finditer("守/等",h):
    if not hist(m.start()): F["B_守等双写/为什么不选矛盾"].append("守/等:"+pl(h[m.start()-10:m.start()+6]))
for kw in ["为什么不选等","为什么不选守"]:
    if kw in h: F["B_守等双写/为什么不选矛盾"].append(kw)
# C 爱德万 公允价/倍数/止盈天数/目标贡献(当日非hist·非异常待核)
for m in re.finditer(r"公允[价]?[¥$]?[\d,]+|约 ?\d+倍|连续 ?\d+ ?个?交易日在|目标贡献[^<]{0,4}[+\-]|最好年份",h):
    if hist(m.start()): continue
    c=pl(h[max(0,m.start()-40):m.start()+10])
    if "爱德万" in c and "异常" not in c and "待核" not in c and "不计算" not in c:
        F["C_爱德万公允价/倍数/止盈天数/目标贡献"].append(pl(h[m.start():m.start()+14]))
# D 闪迪 0.47%与1.8%并存
d47=sum(1 for m in re.finditer("0.47%",h) if not hist(m.start()))
d18=sum(1 for m in re.finditer("1.8%",h) if not hist(m.start()) and "闪迪" in pl(h[max(0,m.start()-40):m.start()+6]))
if d47 and d18: F["D_闪迪0.47%与1.8%并存"].append({"0.47%":d47,"闪迪1.8%":d18})
elif d18: F["D_闪迪0.47%与1.8%并存"].append({"闪迪1.8%残":d18})
# E 非hist旧日今日/昨日差分
for kw in ["今日无重大变化","与昨日一致","动作与昨日","生产于 2026-07-19","数据日 2026-07-19","2026-07-18→2026-07-19"]:
    for m in re.finditer(re.escape(kw),h):
        if not hist(m.start()): F["E_非hist旧日今日昨日差分"].append(kw); break
all_pass=all(not v for v in F.values());mtime=datetime.fromtimestamp(os.path.getmtime(P),JST).isoformat(timespec="seconds")
print(f"★本报告核对版本SHA={sha}")
print("=== gate_fatal3_v4(A/B/C/D/E全HTML) ===")
for k,v in F.items(): print(f"  [{'PASS' if not v else 'FAIL'}] {k}: {v[:3] if v else '无'}")
print(f"★全PASS = {all_pass}")
(ROOT/"data/screen/gate_fatal3_v4.json").write_text(json.dumps({"★本报告核对版本SHA":sha,"版本号":"v4","file":P.name,"字节":len(raw),"mtime":mtime,"ABCDE_FAIL":F,"全PASS":all_pass},ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
