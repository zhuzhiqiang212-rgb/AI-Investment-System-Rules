import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
print("1. 四只旧% 全HTML(当日非hist):")
for old in ["14.2%","6.4%","6.3%","5.7%"]:
    n=[m.start() for m in re.finditer(re.escape(old),h) if not hist(m.start())]
    for pos in n[:3]: print(f"   {old}: ...{pl(h[pos-30:pos+6])[-36:]}")
print("2. '守/等'双写:",sum(1 for m in re.finditer('守/等',h) if not hist(m.start())),"· '为什么不选等/守':",h.count('为什么不选等')+h.count('为什么不选守'))
print("3. 爱德万正文残留:")
for kw in ["27,505","约 ?9倍","9倍","仓位 ?9.0%","9.0%","连续 ?2 ?个交易日","最好年份","留峰值"]:
    for m in re.finditer(kw,h):
        if hist(m.start()): continue
        c=pl(h[m.start()-30:m.start()+8])
        if "爱德万" in c or kw in ("27,505","最好年份","留峰值"): print(f"   [{kw}] ...{c[-38:]}"); break
print("4. 闪迪占比多值:")
for kw in ["0.47%","1.8%","维持1.8%","同额置换","1,350.03","公允55","公允 55"]:
    n=sum(1 for m in re.finditer(re.escape(kw),h) if not hist(m.start()))
    if n: print(f"   {kw}: {n}")
print("5. 旧日今日语境:")
for kw in ["生产于 ?2026-07-19","生产日 ?2026-07-19","价格时点","数据日 ?2026-07-19","2026-07-18→2026-07-19","今日无重大变化","与昨日一致","动作与昨日"]:
    for m in re.finditer(kw,h):
        if not hist(m.start()): print(f"   [{kw}] ...{pl(h[m.start()-10:m.start()+24])}"); break
