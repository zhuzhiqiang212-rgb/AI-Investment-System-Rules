import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
print("=== 1. 触发% (已比加仓价低X% / 还差X%) 当日 ===")
for m in re.finditer(r"已比加仓价低[ 　]*([\d.]+)%",h):
    if not hist(m.start()): print("  已比低",m.group(1)+"%:",pl(h[m.start()-55:m.start()])[-40:])
print("=== 2. 动作闸未通过 ===")
for m in re.finditer(r"动作闸未通过",h):
    if not hist(m.start()): print("  ",pl(h[m.start()-20:m.start()+30])); 
print("  '动作闸未通过'当日数:",sum(1 for m in re.finditer('动作闸未通过',h) if not hist(m.start())))
print("=== 3. 爱德万 目标价/估值合理/倍数 ===")
for kw in ["33,544","+6.5%","6.5%","估值=合理","估值合理","约公允","9倍","目标贡献"]:
    for m in re.finditer(re.escape(kw),h):
        c=pl(h[m.start()-30:m.start()+8])
        if "爱德万" in c or kw in ("33,544","+6.5%","约公允","9倍"):
            print(f"  爱德万'{kw}'[{'HIST' if hist(m.start()) else '当日'}]: ...{c[-38:]}"); break
print("=== 4. 闪迪 市值/占比 ===")
for kw in ["30,390","$30,390","7,597","1.8%","10.8%","4.4pp","4.4"]:
    for m in re.finditer(re.escape(kw),h):
        c=pl(h[m.start()-25:m.start()+10])
        if "闪迪" in c or kw in ("30,390","7,597","10.8%"):
            print(f"  '{kw}'[{'HIST' if hist(m.start()) else '当日'}]: ...{c[-36:]}"); break
print("=== 5. JS 一键全展开 ===")
js="".join(re.findall(r"<script[^>]*>(.*?)</script>",h,re.S))
print("  JS全文:",js[:300])
print("  含details:",bool(re.search(r'details',js)),"· 含open:",bool(re.search(r'open',js)))
