import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
# 清残留守/等双写(generic)→无双写
n=0
for a,b in [("守/等(逐股见统一动作表)","该股7-22动作见统一动作表(逐股唯一答案)"),
            ("7-22守/等·","7-22动作(见统一表)·"),("守/等·今日","该股动作(见统一表)·今日"),
            ("守/等标的","守或等标的"),("=守/等","(见统一表)")]:
    c=h.count(a)
    if c: h=h.replace(a,b); n+=c
# 兜底剩余守/等(当日)→(见统一表)
out,last,m2=[],0,0
for m in re.finditer("守/等",h):
    if hist(m.start()): continue
    out.append(h[last:m.start()]); out.append("守或等(见统一动作表)"); last=m.end(); m2+=1
out.append(h[last:]); h="".join(out)
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
print("清守/等:",n,"+兜底",m2,"· 残留守/等(当日):",sum(1 for m in re.finditer('守/等',h) if not hist(m.start())))
print("字节",len(raw),"乱码",raw.count(b'\xef\xbf\xbd'),"裸LF",raw.count(b'\n')-raw.count(b'\r\n'))
