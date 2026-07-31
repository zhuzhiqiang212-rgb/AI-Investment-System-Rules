import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
log={}
for a,b in [
  ("生产于 2026-07-19 17:51:34","生产于 [724底稿基线2026-07-19·非7-22今日·7-22实时数据见顶部更新层]"),
  ("生产日 2026-07-19（周日·非交易日/市","生产日 [724底稿基线07-19·非7-22今日]（周日·非交易日/市"),
  ("数据日 2026-07-19","数据日 [724底稿基线07-19·7-22实时见顶部更新层]"),
  ("生产日 2026-07-19（周日）","生产日 [724底稿基线07-19·非今日]"),
  ("价格时点：生产日 2026-07-19","价格时点：[724底稿基线·7-22实时价见顶部]"),
  ("2026-07-18→2026-07-19","[724底稿基线差分·非7-22今日]")]:
    c=h.count(a)
    if c: h=h.replace(a,b); log[a[:14]]=c
# 兜底:剩余当日"生产于 2026-07-19"/"数据日 2026-07-19"整token
for tok in ["生产于 2026-07-19","数据日 2026-07-19","生产日 2026-07-19"]:
    out,last,n=[],0,0
    for m in re.finditer(re.escape(tok),h):
        if hist(m.start()): continue
        out.append(h[last:m.start()]); out.append(tok.split(" ")[0]+" [724底稿基线07-19·非7-22今日]"); last=m.start()+len(tok); n+=1
    out.append(h[last:]); h="".join(out)
    if n: log[tok+"兜底"]=n
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
print("stage24c:",log,"· 字节",len(raw),"乱码",raw.count(b'\xef\xbf\xbd'),"裸LF",raw.count(b'\n')-raw.count(b'\r\n'))
resid=sum(1 for kw in ["生产于 2026-07-19","数据日 2026-07-19","生产日 2026-07-19"] for m in re.finditer(re.escape(kw),h) if not hist(m.start()))
print("★旧日期元数据当日残留:",resid)
