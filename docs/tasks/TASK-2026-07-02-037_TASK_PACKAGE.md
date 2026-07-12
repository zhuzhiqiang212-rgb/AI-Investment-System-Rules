# TASK-2026-07-02-037 A方案第一步：扩总则合规闸+建总则Skill+更正角色

## 总则对照
- 第一条唯一出发点：本任务只建立流程合规闸，不从持仓反推投资结论。
- 第六条防静态化自评：新增闸门只检查“是否写出总则对照声明”和“是否自评第六条防静态化”，不锁死任何具体答案；质量链第0闸每日读取目标文件现算，不写死放行对象。
- 只读/安全：不下单、不发布、不动账户/持仓/现金数据。

## 授权
董事长已授权执行 TASK-2026-07-02-037。

## 范围
1. 扩 scripts/skill_gate.py，新增 constitution_gate 与 run_constitution_gate。
2. 新建 skills/constitution_compliance_skill.md。
3. 更正 docs/ROLE_SEPARATION_RULES.md 的现状角色分工并注明 2026-07-02。
4. 在 scripts/quality_chain_check.py 接入第0闸。

## 验证
- py_compile 通过。
- 无总则对照测试文件应 FAIL 并写日志。
- 有总则对照测试文件应 PASS。
- 所有改动文件 UTF-8 重读，问号=0，替换符=0。
