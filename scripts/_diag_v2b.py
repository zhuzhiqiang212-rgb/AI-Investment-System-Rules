import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
# 已比加仓价低 原始(含标签)
for m in re.finditer(r"已比加仓价低",h):
    print("已比加仓价低原始:",repr(h[m.start():m.start()+30]))
print("总:",h.count("已比加仓价低"))
# 还差X%到加仓价 也可能用旧价
print("还差X%到加仓价 数:",len(re.findall(r"还差[ 　]*<?b?>?[\d.]+%",h)))
# 闪迪 30,390 行(市值)+前后
i=h.find(">30,390</td>")
print("闪迪市值30,390行±120:",repr(re.sub('<[^>]+>',' ',h[i-100:i+20])) if i>0 else "?")
# 爱德万33,544 完整
i2=h.find("33,544")
print("爱德万33544±60:",repr(re.sub('<[^>]+>',' ',h[i2-30:i2+40])))
