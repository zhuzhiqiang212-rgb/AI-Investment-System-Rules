import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
守={"US.NVDA","US.AVGO","US.TSM","JP.6857","JP.9984","JP.4568","US.SPCX"}
GPT={s:("守" if s in 守 else "等") for s in ["JP.4568","US.NVDA","US.MSFT","US.MSTR","US.COIN","JP.9984","JP.8766","JP.6758","JP.6857","JP.7203","JP.8001","JP.7832","JP.7974","US.AVGO","US.CRCL","US.SNDK","US.TSM","US.META","US.IBKR","US.SPCX"]}
NAME={"JP.4568":"第一三共","US.NVDA":"英伟达","US.MSFT":"微软","US.MSTR":"MSTR","US.COIN":"Coinbase","JP.9984":"软银","JP.8766":"东京海上","JP.6758":"索尼","JP.6857":"爱德万","JP.7203":"丰田","JP.8001":"伊藤忠","JP.7832":"万代","JP.7974":"任天堂","US.AVGO":"博通","US.CRCL":"Circle","US.SNDK":"闪迪","US.TSM":"台积电","US.META":"META","US.IBKR":"IBKR","US.SPCX":"SpaceX"}
def pl(s): return re.sub(r"\s+"," ",re.sub("<[^>]+>"," ",s)).strip()
# 增补⑥前瞻表:name code <td center>action</td>
i=h.find("增补⑥")
seg=h[i:i+9000] if i>0 else h
print("=== 增补⑥前瞻表 各股action ===")
for sym,g in GPT.items():
    m=re.search(re.escape(NAME[sym])+r"</td><td>"+re.escape(sym)+r'</td><td style="text-align:center">([^<]*)</td>',seg)
    if m:
        act=pl(m.group(1))
        flag="★≠"+g if g not in act and act not in("守","等·盯","等·待核") else ("★≠"+g if (g=="守" and act!="守") or (g=="等" and act not in("等","等·盯","等·待核")) else "ok")
        if flag!="ok": print(f"  {NAME[sym]}({sym}): 增补⑥={act} 应{g} {flag}")
print("(未列=一致)")
