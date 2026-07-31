import hashlib, json, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
LOCK = ROOT/"00_请先看这里"/"★每日产品_2026-07-22_locked_v1.html"
raw = LOCK.read_bytes(); sha = hashlib.sha256(raw).hexdigest()
reg = {
 "_说明": "产品版本登记表(GPT#1头等·锁版本)。核对/送验/复验必对同一SHA·锁定版不覆盖·新改另存新版本号。",
 "生成于": datetime.now(JST).isoformat(timespec="seconds"),
 "★当前锁定送验版": {
   "版本号": "v1", "文件名": LOCK.name, "SHA256": sha, "字节": len(raw),
   "mtime": datetime.fromtimestamp(os.path.getmtime(LOCK), JST).isoformat(timespec="seconds"),
   "乱码": raw.count(b"\xef\xbf\xbd"), "裸LF": raw.count(b"\n")-raw.count(b"\r\n"),
   "说明": "★GPT复验/架构师核对/董事长执行 全部指定此SHA·此文件此后不覆盖不改名",
 },
 "同名文件↔各版本SHA对应表": {
   "同名工作文件(可能被后续覆盖)": {"文件名": "★每日产品_2026-07-22.html", "当前SHA": sha, "警告": "工作文件·非验收依据·以locked_v1的SHA为准"},
   "v1锁定版(当前送验)": {"文件名": LOCK.name, "SHA256": sha},
 },
 "历史送验版本登记(脱节·作废·仅留痕)": [
   {"SHA前缀": "ead88f4b", "说明": "GPT曾误验此旧版(版本脱节根因)·作废"},
   {"SHA前缀": "820a4b51", "说明": "闰迪估值区未退出前·作废"},
   {"SHA前缀": "2eb0a380", "说明": "第一三共顶部等vs守未修前·作废"},
   {"SHA前缀": "135071540c", "说明": "更早语义修正中间态·作废"},
   {"SHA前缀": "a4724e1e", "说明": "=当前v1锁定版内容(定稿·前身文件名v1定稿_a4724e1e)·已规范化为locked_v1"},
 ],
 "锁版本规则": "定稿即冻结为 ★每日产品_YYYY-MM-DD_locked_vN.html·登记本表·不覆盖·后续改动另存 locked_v(N+1)·报告首行写死『本报告核对版本SHA=xxx』。",
}
out = ROOT/"data/screen/product_version_registry.json"; out.write_text(json.dumps(reg, ensure_ascii=False, indent=1)+"\n", encoding="utf-8")
print("锁定版SHA:", sha)
print("registry:", out)
