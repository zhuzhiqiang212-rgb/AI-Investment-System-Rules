import hashlib, os, json
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path("G:/我的云端硬盘/AI_Investment_System")
canon = ROOT / "00_请先看这里" / "★每日产品_2026-07-22.html"
raw = canon.read_bytes()
sha = hashlib.sha256(raw).hexdigest()
ver = ROOT / "00_请先看这里" / f"★每日产品_2026-07-22_v1定稿_{sha[:8]}.html"
vraw = ver.read_bytes() if ver.exists() else b""
vsha = hashlib.sha256(vraw).hexdigest() if vraw else ""
manifest = {
    "_说明": "版本锁定登记(GPT#1头等·冻结即登记·不覆盖同名·核对/送验/复验必对同一SHA)",
    "生成于": datetime.now(JST).isoformat(timespec="seconds"),
    "冻结版本": {"文件名": ver.name, "SHA256": vsha, "字节": len(vraw),
              "mtime": datetime.fromtimestamp(os.path.getmtime(ver), JST).isoformat(timespec="seconds") if ver.exists() else ""},
    "同名文件↔送验版本对应表": {
        "同名工作文件": {"文件名": "★每日产品_2026-07-22.html", "SHA256": sha, "字节": len(raw),
                    "mtime": datetime.fromtimestamp(os.path.getmtime(canon), JST).isoformat(timespec="seconds"),
                    "说明": "工作文件·可能被后续覆盖·验收以冻结版SHA为准"},
        "本次送验冻结版": {"文件名": ver.name, "SHA256": vsha, "说明": "★GPT复验必对此SHA·此文件此后不改名不覆盖"},
        "历史送验SHA(脱节·作废)": ["ead88f4b(旧·GPT曾误验)", "820a4b51", "2eb0a380", "135071540c(旧)"],
    },
    "锁版本规则": "此后新版本用新文件名/版本号(vN定稿_SHA前8)·绝不覆盖已冻结版·核对/送验/复验三方必对同一SHA。",
}
out = ROOT / "data/screen/version_lock_20260722.json"
out.write_text(json.dumps(manifest, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print("冻结版SHA:", vsha[:16], "· 字节:", len(vraw), "· 工作文件SHA:", sha[:16], "· 一致:", sha == vsha)
print("登记:", out.name)
