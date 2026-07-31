import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
print("=== 5旧价 当日残留(非hist·非历史stat语境) ===")
for old in ["¥5,424","$202.55","¥2,791","¥7,526","¥27,505"]:
    for m in re.finditer(re.escape(old),h):
        if hist(m.start()): continue
        pre=pl(h[m.start()-40:m.start()])
        tag="历史stat" if any(x in pre for x in ["最低","最高","52周","上沿","20个交易日","5月","创新高","回调"]) else "★当日双价"
        print(f"  {old} [{tag}]: ...{pre[-40:]}")
print("=== 闪迪估值区异常数 全位置 ===")
for kw in ["$40~$80","$40~80","中枢$55","中枢 $55","$55","现价 $1,350","$1,350"]:
    for m in re.finditer(re.escape(kw),h):
        if hist(m.start()): continue
        print(f"  {kw}: ...{pl(h[m.start()-22:m.start()+14])[-32:]}")
        break
