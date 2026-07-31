import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# 今日触发区 = "今天有没有跌到你的加仓价" 之后
i=h.find("今天有没有跌到你的加仓价")
seg=h[i:i+6000] if i>0 else ""
print("今日触发区锚@",i)
print("=== ⚡已触发 全产品(当日非hist) ===")
for m in re.finditer("⚡已触发",h):
    if not hist(m.start()): print(f"  @{'触发区内' if i<m.start()<i+6000 else '别处'}: {pl(h[m.start():m.start()+40])}")
print("已触发总(当日):", sum(1 for m in re.finditer('已触发',h) if not hist(m.start())))
print("=== 今日触发区 现价值(是否7-22) ===")
for m in re.finditer(r"现价 <b>[¥$][\d,]+\.?\d*</b>",seg):
    print("  ",pl(m.group()))
print("=== 旧价在今日触发区 ===")
for old in ["5,424","202.55","2,791","7,526","27,505"]:
    if old in seg: print(f"  ★旧价{old}在今日触发区!")
print("=== 第一三共 顶部动作(增补⑪统一表 vs 别处) ===")
for m in re.finditer(r"第一三共[^\n<]{0,30}",h):
    t=pl(m.group())
    if any(x in t for x in ["等","守","加"]) and "研究" not in t and "完整" not in t:
        z='HIST' if hist(m.start()) else '当日'
        print(f"  [{z}] {t[:50]}")
