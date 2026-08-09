# -*- coding: utf-8 -*-
"""★★★轮218 GPT V7指定自测(就1条·不扩大):无決算短信场景 → ①环停住·A档=False·断点写明。
★这条是【修正1 真的生效】的唯一证明(无決算短信不得退回选任意最新公告)。
★用假索引(只有業績予想/自己株式取得)mock·不走网络·不碰真key。"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import jquants_pipeline as jp


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    def fake_api(path, key, params=None):
        if path == "/td/list":
            return 200, json.dumps({"data": [
                {"DiscNo": "X1", "Code": "99990", "Title": "業績予想および配当予想に関するお知らせ", "DiscDate": "2026-07-24", "DiscTime": "15:00"},
                {"DiscNo": "X2", "Code": "99990", "Title": "自己株式取得に係る事項の決定に関するお知らせ", "DiscDate": "2026-07-20", "DiscTime": "15:00"},
            ]}).encode()
        return 200, b"{}"
    jp._api = fake_api
    jp._key = lambda: "DUMMY_NOT_REAL"    # ★不读真key
    o = jp.run("9999", "JP.9999")
    ok1 = (o["五环"][0]["通过"] is False)
    a_closed = (o.get("★A档开放") is False)
    dianpo = "无決算短信" in (o.get("★断点") or "")
    only_ring1 = (len(o["五环"]) == 1)
    print("①环停住(通过=False):", ok1)
    print("A档开放=False:", a_closed)
    print("断点写明无決算短信:", dianpo, "→", o.get("★断点"))
    print("②-⑤未执行(只①环):", only_ring1)
    passed = ok1 and a_closed and dianpo and only_ring1
    print("═══ 无決算短信自测:", "PASS" if passed else "FAIL", "═══")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
