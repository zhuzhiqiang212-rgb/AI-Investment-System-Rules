import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
top=h.find('<div id="topnav"')
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# 第一三共/JP.4568 在顶部增补层的动作显示
print("=== 第一三共/JP.4568 顶部增补层动作 ===")
for m in re.finditer(r"(第一三共|JP\.4568)",h):
    if m.start()>=top: continue
    w=pl(h[m.start():m.start()+80])
    if any(x in w for x in ["守","等","加","减","盯"]): print("  顶部:",w[:70])
# 增补⑪统一动作表 第一三共行
i=h.find("unified-action-0722")
if i>0:
    seg=h[i:i+6000]
    m=re.search(r"第一三共.*?JP\.4568.*?</tr>",seg,re.S)
    if m: print("统一动作表第一三共行:",pl(m.group())[:90])
# 爱德万/闪迪 今日触发区
print("=== 爱德万/闪迪 今日触发区(异常待核?) ===")
ti=h.find("今天有没有跌到你的加仓价")
tseg=h[ti:ti+6000]
for who in ["爱德万","闪迪"]:
    for m in re.finditer(who+r"[^\n]{0,80}",tseg):
        print(f"  {who}:",pl(m.group())[:75]); break
