import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
lines=h.split("\n")
def hist_line(ln):
    pos=sum(len(lines[k])+1 for k in range(ln))
    return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
for ln in [2043,2044,2045,2065,2066,2067,1654,1655,1656,1723,1724,1725]:
    if ln<len(lines):
        t=re.sub("<[^>]+>"," ",lines[ln])
        if t.strip():
            print(f"L{ln}[{'HIST' if hist_line(ln) else '当日'}]:", t.strip()[:150])
print("--- 闪迪估值区 $40~$80/中枢$55/$1,350 全位置 ---")
for kw in ["$40~$80","$40~80","中枢$55","中枢 $55","$1,350","$1,519.49"]:
    c=h.count(kw); 
    if c: 
        i=h.find(kw); print(f"  '{kw}'×{c} @行{h[:i].count(chr(10))}: ...{re.sub('<[^>]+>','',h[i-25:i+15])}")
