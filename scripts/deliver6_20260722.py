import hashlib, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
VER = ROOT / "00_请先看这里" / "★每日产品_2026-07-22_v1定稿_a4724e1e.html"
raw = VER.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
prod = {x["symbol"]: x for x in json.loads((ROOT/"data/reports/production_20260722.json").read_text(encoding="utf-8"))["holdings"]}
守 = {"US.NVDA","US.AVGO","US.TSM","JP.6857","JP.9984","JP.4568","US.SPCX"}
px = {prod[s]["name"]: {"7-22唯一正式现价": f"{'¥' if s.startswith('JP') else '$'}{prod[s]['price']:,.2f}",
      "用途": "顶部全持仓表/L1动作表/L2/L3/今日触发区 现价统一用此值", "动作": ("守" if s in 守 else "等")} for s in prod}
d = {
 "_说明": "GPT复验退回·版本锁定+三致命区硬闸·6送验材料(对冻结版a4724e1e)",
 "生成于": datetime.now(JST).isoformat(timespec="seconds"),
 "①新HTML+SHA/字节/mtime": {"文件名": VER.name, "SHA256": sha, "字节": len(raw),
    "mtime": datetime.fromtimestamp(os.path.getmtime(VER), JST).isoformat(timespec="seconds"), "乱码": raw.count(b"\xef\xbf\xbd"), "裸LF": raw.count(b"\n")-raw.count(b"\r\n")},
 "②三致命区自动扫描原始结果": "data/screen/gate_3zones_20260722.json(A守等加仓语义/B今日触发区现价≠7-22/C异常标的估值参与/D JS读hist·全PASS)",
 "③人工vs自动发现对照": [
   {"人工(架构师/GPT)发现": "今日触发区旧价¥5,424/$202.55进今日现价+已触发", "现根因": "版本脱节·GPT验旧版·当前冻结版今日触发区全7-22价·⚡已触发=0", "自动硬闸": "B区扫描·PASS"},
   {"人工发现": "第一三共顶部等vs统一表守", "本轮修": "增补⑥前瞻表等→守(2处)·顶部残留=0", "自动硬闸": "A/全层动作·PASS"},
   {"人工发现": "闪迪估值区$40~80/$1,350漏退出", "本轮修": "行2043/2065退出→异常待核·残留0", "自动硬闸": "C区扫描·PASS"},
 ],
 "④每只唯一现价及价格用途表": px,
 "⑤爱德万闪迪异常节点退出清单": {
   "爱德万(JP.6857)": ["今日价值区¥2646~3234→异常待核","加仓价¥2,646/中间值¥2,940/还差939.5%→退出","止盈¥27,505→退出","¥2,938 PE推算→退出"],
   "闪迪(US.SNDK)": ["中周期公允$35~95→异常待核","估值区$40~$80/中枢$55/现价$1,350(行2043/2065)→退出","股数20→5(留痕)"],
   "退出后只显": "价格/复权口径异常待核·不计算估值/加仓价/止盈线/目标贡献/买卖·见增补⑮",
 },
 "⑥同名文件↔送验版本对应关系": "data/screen/version_lock_20260722.json(冻结版a4724e1e=GPT复验必对此SHA·同名工作文件可能被后续覆盖·历史脱节SHA作废)",
 "五道硬闸": {"三致命区A/B/C/D": "全PASS","gate_v5矩阵20×10": "全PASS","gate_v4逐股+语义": "全PASS","退化硬闸15项": "全通过","逐对象v3": "10/10"},
}
out = ROOT/"data/screen/deliver6_20260722.json"; out.write_text(json.dumps(d, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
print("落 deliver6_20260722.json · 冻结版SHA:", sha)
