#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""★轮336 乙2:通用「退出0必须伴随产出」闸(可复用)。

董事长原话:「报『没做到』不扣分，假报『做到了』是信任击穿。」★退出码0 就是机器版的『我做到了』。
→ 任何 build/pipeline 脚本:退出码0 却【没有任何"我做了什么"的结构化产出】(写了产物文件 或 打了摘要)→ 强制非0。

用法(在脚本 __main__ 里)：
    from exit_guard import guarded
    if __name__ == "__main__":
        guarded(main, produced=lambda: OUT_PATH.exists())   # main 返回0 但 produced()=False → 退非0
    # 或按步骤计数：
        guarded(main, steps_ran=lambda: MODULE._STEPS_RAN)   # 返回0 但 steps_ran()==0 → 退非0
"""
import sys, traceback


def guarded(main_fn, produced=None, steps_ran=None, on_fail=None):
    """跑 main_fn·堵『退出0＝报成功』洞:
    ①异常抛顶→不吞·非0(exit 3)。②返回0 却 produced()=False 或 steps_ran()==0 → 强制非0(exit 3)。
    produced/steps_ran 为可调用·任一给出即校验。on_fail(reason) 可选回调(记台账等)。"""
    try:
        rc = main_fn()
    except SystemExit:
        raise
    except BaseException as e:
        traceback.print_exc()
        if on_fail:
            try:
                on_fail(f"异常抛到顶:{type(e).__name__}:{e}")
            except Exception:
                pass
        raise SystemExit(3)
    if rc in (0, None):
        no_output = False
        why = ""
        if steps_ran is not None:
            try:
                if int(steps_ran() or 0) == 0:
                    no_output, why = True, "零步骤(没跑任何一步)"
            except Exception:
                pass
        if produced is not None:
            try:
                if not produced():
                    no_output, why = True, "退出0却无产物文件"
            except Exception:
                pass
        if no_output:
            print(f"[★exit_guard 乙2·轮336] 退出码0 但{why} → 强制非0(假报做到了=信任击穿)", file=sys.stderr)
            if on_fail:
                try:
                    on_fail(f"退出0却零产出:{why}")
                except Exception:
                    pass
            raise SystemExit(3)
    raise SystemExit(rc or 0)
