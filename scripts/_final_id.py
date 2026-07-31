import hashlib, os, re
from datetime import datetime, timezone, timedelta
JST = timezone(timedelta(hours=9))
P = "00_请先看这里/★每日产品_2026-07-22.html"
raw = open(P, "rb").read(); h = raw.decode("utf-8")
print("字节:", len(raw), "SHA256:", hashlib.sha256(raw).hexdigest())
print("mtime:", datetime.fromtimestamp(os.path.getmtime(P), JST).isoformat(timespec="seconds"), "乱码:", raw.count(bytes([239,191,189])), "裸LF:", raw.count(bytes([10]))-raw.count(bytes([13,10])))
r1 = len(re.findall(r"第一档[ 　]?[$¥][0-9,.]+", h)) + len(re.findall(r"第二档[ 　]?[$¥][0-9,.]+", h))
print("残留第一档/第二档带价:", r1, "待建仓:", h.count("待建仓"), "买卖建议双档并列:", h.count("买卖建议·双档并列"), "c-add:", h.count("chip c-add"))
