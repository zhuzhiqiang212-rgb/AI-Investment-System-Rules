import re
from pathlib import Path
p=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html")
h=p.read_bytes().decode("utf-8")
def hist(pos): return h.rfind('class="hist-iso"',0,pos)>h.rfind("</details>",0,pos)
# 闪迪占比/拖累 残留
for kw in ["闪迪1.8%","1.8%","10.8%","4.4pp","4.4个百分点","拖累"]:
    for m in re.finditer(re.escape(kw),h):
        if not hist(m.start()) and ("闪迪" in re.sub('<[^>]+>','',h[m.start()-25:m.start()+8]) or kw in ("10.8%","4.4pp")):
            print(f"{kw}: ...{re.sub('<[^>]+>',' ',h[m.start()-28:m.start()+12])}"); break
# 修:闪迪占比整块退出(含空格变体)
n=0
for a,b in [("爱德万9.0%+闪迪1.8%= 10.8%·超限一倍","爱德万9.0%（★闪迪股数×价核准前不计占比·原闪迪1.8%/合计10.8%基于错误20股市值·已退出）"),
            ("闪迪1.8%","闪迪[占比待核·核准前不计入]"),
            ("拖累4.4pp","拖累[闪迪待核·不计入]"),("拖累 4.4pp","拖累[闪迪待核·不计入]"),("4.4个百分点","[闪迪待核·不计入]")]:
    c=h.count(a)
    if c: h=h.replace(a,b); n+=c; print(f"改 {a[:16]}: {c}")
p.write_bytes(h.encode("utf-8"))
raw=p.read_bytes()
print("闪迪占比/拖累退出:",n,"· 字节",len(raw),"乱码",raw.count(b'\xef\xbf\xbd'),"裸LF",raw.count(b'\n')-raw.count(b'\r\n'))
print("残留 闪迪1.8%(当日):",sum(1 for m in re.finditer('闪迪1.8%',h) if not hist(m.start())),"· 10.8%:",sum(1 for m in re.finditer('10.8%',h) if not hist(m.start())))
