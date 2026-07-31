import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
for m in re.finditer(r"\$35~95", h):
    print("残:", re.sub("<[^>]+>","",h[m.start()-30:m.start()+8]))
# 清所有 $35~95 / ($35 / 35~95 闪迪估值
out,last,n=[],0,0
for m in re.finditer(r"\(?\$35~95\)?", h):
    if hist(m.start()): continue
    out.append(h[last:m.start()]); out.append("[异常待核·闪迪价格/复权口径异常]"); last=m.end(); n+=1
out.append(h[last:]); h="".join(out)
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
print("清$35~95:",n,"· 残留:",h.count("$35~95"),"· 字节",len(raw),"乱码",raw.count(b"\xef\xbf\xbd"),"裸LF",raw.count(b"\n")-raw.count(b"\r\n"))
