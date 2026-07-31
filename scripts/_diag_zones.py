import re
from pathlib import Path
h=Path("G:/我的云端硬盘/AI_Investment_System/00_请先看这里/★每日产品_2026-07-22.html").read_bytes().decode("utf-8")
# 今日触发区结构
i=h.find("今天有没有跌到你的加仓价")
print("今日触发区锚点@",i)
print("其前<table>@",h.rfind("<table",0,i),"· 其前<div class@",h.rfind('<div class',0,i))
# 任天堂行原始
j=h.find("加仓价(便宜位)")
print("加仓价行±120原始:",repr(h[j-90:j+40]))
# 该区容器
print("承接节点@",h.find("承接节点"),"· card-triggers@",h.find("card-triggers"))
# 待拍板/组合目标/差分 锚点
for kw in ["待拍板","组合","离目标","目标贡献","今日与昨日","差分"]:
    print(f"  '{kw}'@ {h.find(kw)} 计数{h.count(kw)}")
