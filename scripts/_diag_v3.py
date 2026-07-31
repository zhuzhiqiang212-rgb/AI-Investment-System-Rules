import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# 爱德万/闪迪 "估值=X" 或 估值合理/极贵 全位置(当日)
print("=== 爱德万/闪迪 '估值=/估值合理/极贵' 当日 ===")
for m in re.finditer(r"估值[=＝][^·，。<、|｜]{0,8}|估值合理|估值 ?= ?合理",h):
    if hist(m.start()): continue
    ctx=pl(h[m.start()-40:m.start()+12])
    if "爱德万" in ctx or "闪迪" in ctx:
        who="爱德万" if "爱德万" in ctx else "闪迪"
        print(f"  [{who}] @行{h[:m.start()].count(chr(10))}: ...{ctx[-46:]}")
# 前瞻预测表(增补⑥)爱德万行
i=h.find("增补⑥")
seg=h[i:i+9000] if i>0 else h
m=re.search(r"爱德万</td>.*?</tr>",seg,re.S)
if m: print("增补⑥爱德万行:",pl(m.group())[:130])
m2=re.search(r"闪迪</td>.*?</tr>",seg,re.S)
if m2: print("增补⑥闪迪行:",pl(m2.group())[:130])
