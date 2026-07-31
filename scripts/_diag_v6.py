import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
def hist(p): return h.rfind('class="hist-iso"',0,p)>h.rfind("</details>",0,p)
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
def card(idk,sym):
    i=h.find(f'id="{idk}-{sym}"')
    if i<0: return "",-1
    nx=[x for k in("act","why","deep") for x in [h.find(f'id="{k}-',i+12)] if x>0]
    return h[i:(min(nx) if nx else len(h))],i
KW=["约9倍","8.5倍","中周期合理值","中周期","极贵","景气高点","峰值定价","现价约合理上沿","现价约为中周期合理值","穿牛熊","合理值","公允"]
for who,sym in [("爱德万","JP.6857"),("闪迪","US.SNDK")]:
    print(f"=== {who} 整卡(act/why/deep) 异常估值表述 ===")
    for idk in ["act","why","deep"]:
        seg,pos=card(idk,sym)
        for kw in KW:
            if kw in seg:
                j=seg.find(kw)
                if not hist(pos+j): print(f"  [{idk}] '{kw}': ...{pl(seg[j-25:j+12])[-34:]}")
# line173残句
i=h.find("守（因数据未核准")
print("=== line173残句(双句号/重复) ===")
if i>0: print("  ",repr(pl(h[i-10:i+90])))
# line906/955归属
for kw in ["倍数压向高20","高 20/低 30倍","¥2,939 落中周期公允","2,939落中周期"]:
    j=h.find(kw)
    if j>0: print(f"  '{kw}'@行{h[:j].count(chr(10))}: ...{pl(h[j-40:j+20])[-50:]}")
