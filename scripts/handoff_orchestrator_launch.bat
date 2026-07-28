@echo off
REM T024/CODE-20 接力器启动器(Windows任务计划调用·每次轮询一次)
cd /d "G:\我的云端硬盘\AI_Investment_System"
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
python scripts\handoff_orchestrator.py --once >> "data\orchestration\logs\launch_stdout.log" 2>&1
