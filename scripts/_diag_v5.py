import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# "今天哪些数据不能依赖"区
i=h.find("今天哪些数据不能依赖")
print("不能依赖区锚@",i)
if i<0:
    for kw in ["不能依赖","数据不能","不可依赖","公允 3000","公允3000","公允 55"]:
        j=h.find(kw); print(f"  '{kw}'@{j}")
# 爱德万/闪迪 公允/倍数全位置(当日非hist)
print("=== 爱德万/闪迪 公允/倍数 全位置 ===")
for m in re.finditer(r"公允[ ]?\d[\d,]*|约 ?\d+ ?倍|中周期公允|\d+\.?\d* ?倍",h):
    if hist(m.start()): continue
    c=pl(h[max(0,m.start()-42):m.start()+14])
    if "爱德万" in c or "闪迪" in c or "27505" in c or "1350" in c or "3000" in c or "55 的" in c:
        print(f"  @行{h[:m.start()].count(chr(10))}: ...{c[-52:]}")
