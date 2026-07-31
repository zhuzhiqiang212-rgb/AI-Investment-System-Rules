import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# 爱德万/闪迪 全context 任何 [¥$]数字 或 X% (当日非hist·排除已标异常/现价7-22)
for who,rp in [("爱德万","¥29,585"),("闪迪","$1,519.49")]:
    print(f"=== {who} 邻近数字(当日·非7-22现价·非异常标注) ===")
    hits=0
    for m in re.finditer(who,h):
        if hist(m.start()): continue
        win=h[m.start():m.start()+150]
        for nm in re.finditer(r"[¥$][\d,]+(?:\.\d+)?|[\d.]+%",win):
            v=nm.group()
            pre=pl(win[max(0,nm.start()-14):nm.start()])
            if v in (rp,) or "异常" in pre or "待核" in pre or "不计算" in pre or "增补⑮" in win[nm.start()-30:nm.start()]: continue
            # 只报 加仓价/止盈/目标/组合/还差/公允 语境
            if any(z in win[:nm.start()] for z in ["加仓价","止盈","目标贡献","组合贡献","还差","公允","中间值","价值区"]):
                print(f"  ★{who} {v} 语境:{pl(win[:nm.start()])[-30:]}"); hits+=1; 
                if hits>=4: break
        if hits>=4: break
    if not hits: print("  无残留(全退出/已标异常)")
