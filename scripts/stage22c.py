import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
n=0
for a,b in [("= 10.8%·超限一倍","（闪迪股数×价核准前·合计占比待核·爱德万9.0%单只未超20%）"),
            ("=10.8%·超限一倍","（闪迪待核·合计占比待核）"),
            ("10.8%·超限","（合计待核·闪迪未计入）超限")]:
    c=h.count(a)
    if c: h=h.replace(a,b); n+=c; print("清",a[:14],c)
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
# 验闪迪股数×价=市值
import json
prod={x['symbol']:x for x in json.load(open('data/reports/production_20260722.json',encoding='utf-8'))['holdings']}
sndk=prod['US.SNDK']; print("闪迪 5股×$1,519.49 =", round(5*1519.49,2), "· 产品市值cell=7,597?", "7,597" in h)
print("残留 10.8%(当日):",sum(1 for m in re.finditer('10.8%',h) if not hist(m.start())),"· 字节",len(raw),"乱码",raw.count(b'\xef\xbf\xbd'),"裸LF",raw.count(b'\n')-raw.count(b'\r\n'))
