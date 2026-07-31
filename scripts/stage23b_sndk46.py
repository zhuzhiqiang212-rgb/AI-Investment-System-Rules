import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
n=0
# 闪迪 46倍TTM按峰值定价 → 异常待核(仅闪迪语境)
for a in ["约46倍TTM按峰值定价","46倍TTM按峰值定价","46倍TTM"]:
    c=h.count(a)
    if c: h=h.replace(a,a.replace("46倍TTM","[异常待核·不计算倍数]TTM")); n+=c; print("改",a,c)
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
# 验闪迪46倍残留
resid=sum(1 for m in re.finditer(r"[\d.]+倍",h) if not hist(m.start()) and ("闪迪" in re.sub('<[^>]+>','',h[m.start()-46:m.start()]) or "闪迪" in re.sub('<[^>]+>','',h[m.start():m.start()+20])))
print("字节",len(raw),"乱码",raw.count(b'\xef\xbf\xbd'),"裸LF",raw.count(b'\n')-raw.count(b'\r\n'))
print("★闪迪倍数当日残留:",resid)
