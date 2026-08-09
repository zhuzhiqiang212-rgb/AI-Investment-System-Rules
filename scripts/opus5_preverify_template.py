# -*- coding: utf-8 -*-
"""★轮85 CG7-3:八步流程第6步(产品初验)落地——建 Opus5 初验清单模板(固定格式)。
→ 00_任务中心/初验_{date}.md·含三项硬指标+模块闸+完工度。★Code只建模板+自动填机器可核部分·结论由Opus5填。"""
import sys, json, argparse
from datetime import datetime, timezone, timedelta
from pathlib import Path
JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent


def _rj(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return {}


def build(date):
    dc = date.replace("-", ""); dh = "%s-%s-%s" % (dc[:4], dc[4:6], dc[6:])
    man = _rj(ROOT / "data/product_manifest.json")
    cs = _rj(ROOT / "data/logs" / f"completion_status_{dc}.json")
    prod_exists = (ROOT / "data/reports" / f"production_{dc}.json").exists()
    run_id = man.get("run_id", "?")
    header = cs.get("★页头串", "?")
    done = cs.get("★机器装好了")
    L = []
    L.append(f"# 产品初验清单 · {dh}（Opus5 第6步·固定格式·机器预填+Opus5判结论）\n")
    L.append("## 一、三项硬指标（机器可核）")
    L.append(f"- [{'x' if prod_exists else ' '}] ① production_{dc}.json 存在：**{prod_exists}**")
    L.append(f"- [{'x' if dh in str(man.get('data_date','')) or dc in str(man.get('data_date','')) else ' '}] ② data_date = {dh}：manifest={man.get('data_date')}")
    L.append(f"- [{'x' if run_id!='?' else ' '}] ③ run_id：**{run_id}**\n")
    L.append("## 二、模块完整性闸（machine·必需模块）")
    L.append("- 由 module_completeness_gate 核：必需模块全在=PASS（见渲染日志『必需 N/N 在』）\n")
    L.append("## 三、完工度自检")
    L.append(f"- 机器自报：**{header}**")
    L.append(f"- 机器装好了：**{done}** → {'可进初验放行流程' if done else '★未装好·产品标「未完工·内部件」·不交董事长'}\n")
    L.append("## 四、Opus5 初验结论（★人工填·Code不代填）")
    L.append("- [ ] 判断/概率/理由是否与我的定稿一致：____")
    L.append("- [ ] 八节内容是否照录未被改写：____")
    L.append("- [ ] 清单未过而报可交＝误判（记 judgment_scorecard）——本产品清单是否全过：____")
    L.append("- **初验结论（PASS/PARTIAL/FAIL）**：____")
    L.append(f"\n---\n机器预填时间：{datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S JST')}｜Code 只填机器可核部分·结论由 Opus5 判。")
    return "\n".join(L), done


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(); ap.add_argument("--date", required=True); a = ap.parse_args()
    md, done = build(a.date)
    p = ROOT / "00_任务中心" / f"初验_{a.date.replace('-', '')}.md"
    p.write_text(md + "\n", encoding="utf-8")
    b = p.read_bytes()
    print("[opus5_preverify_template] %s → %s · 乱码%d · 机器装好=%s" % (
        a.date, p.name, b.count(b"\xef\xbf\xbd"), done))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
