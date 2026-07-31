# -*- coding: utf-8 -*-
"""GPT V6 §三.5 失败关闭硬闸自动测试：4 种失败均须得【整轮 FAILED】，不得 SUCCESS。
覆盖:①子步超时 ②子步返回非零 ③必需文件缺失 ④JSON必填字段不足 (+反例:正常不误杀)。
用法: python scripts/test_failgate.py   (退出码 0=全通过)"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import daily_auto_produce as dap  # noqa: E402
ROOT = dap.ROOT
D = "29990101"  # 远期测试日·避免与真数据碰撞
res = []


def ck(name, cond):
    res.append((name, bool(cond)))


# ① 子步超时 → run_step 返回 124 → critical_step_failed 判 FAILED
sl = ROOT / "scripts" / "_test_sleep_tmp.py"
sl.write_text("import time\ntime.sleep(30)\n", encoding="utf-8")
rc, _ = dap.run_step("t超时", "_test_sleep_tmp.py", D, timeout=2)
ck("①子步超时→rc=124", rc == 124)
ck("①超时→整轮FAILED", dap.critical_step_failed(D, "_test_sleep_tmp.py", True, rc) is not None)
sl.unlink()

# ② 子步返回非零 → FAILED
ex = ROOT / "scripts" / "_test_exit1_tmp.py"
ex.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
rc, _ = dap.run_step("t非零", "_test_exit1_tmp.py", D, timeout=30)
ck("②子步非零→rc!=0", rc != 0)
ck("②非零→整轮FAILED", dap.critical_step_failed(D, "_test_exit1_tmp.py", True, rc) is not None)
ex.unlink()

# ③ 必需文件缺失(rc=0 也 FAILED) → 防后续渲染掩盖上游失败
ok, why = dap.verify_output(D, "production_pipeline.py")
ck("③必需文件缺失→verify False", (not ok) and ("缺失" in why))
ck("③缺件→rc0也整轮FAILED", dap.critical_step_failed(D, "production_pipeline.py", True, 0) is not None)

# ④ JSON 必填字段不足(rc=0 也 FAILED)
f = ROOT / "data" / "accounts" / f"holdings_true_{D}.json"
f.write_text(json.dumps({"padding": "x" * 300, "nothing": 1}), encoding="utf-8")  # >200B·过大小检查·仅缺 holdings 字段
ok, why = dap.verify_output(D, "holdings_true_autobuild.py")
ck("④JSON字段不足→verify False", (not ok) and ("字段不足" in why))
ck("④字段不足→rc0也整轮FAILED", dap.critical_step_failed(D, "holdings_true_autobuild.py", True, 0) is not None)
f.unlink()

# ⑤ 反例:真实 2026-07-29 production 正常 → 不得误杀成 FAILED
ok29, _ = dap.verify_output("20260729", "production_pipeline.py")
ck("⑤正常production→不误杀(verify True)", ok29)
ck("⑤正常→critical_step_failed=None", dap.critical_step_failed("20260729", "production_pipeline.py", True, 0) is None)

allpass = all(c for _, c in res)
for n, c in res:
    print(("PASS " if c else "FAIL ") + n)
print("\n★4 种失败均→整轮 FAILED，正常不误杀：", "全通过" if allpass else "有失败")
sys.exit(0 if allpass else 1)
