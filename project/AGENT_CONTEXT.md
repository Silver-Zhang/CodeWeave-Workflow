# CodeWeave 接手上下文

1. 当前[B模式M2-R0](tasks/2026-10/20261020_01_m2-workspace-architecture/README.md)设计交付完成，完整v2独立ACCEPT/implementation_ready=true；建议用户冻结设计并安排M2-A。设计通过不是生产实现PASS；本轮禁止main合并/tag/发布/私有项目/M2生产实现，用户冻结与后续实施另计。
2. CodeWeave feat/m1-interactive-map仍HEAD6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7，tree ffabf3d59a334349126ae2fec9923660d844e597，工作区干净。M0为0e9c093a，main仍676f63d4；未改源码/测试。工作流project/codeweave本轮base39f4ae9de970106adf060a5af54ac0f850a99394，结果SHA见交付消息/Git引用。
3. 真实核对历史M0接受34文件hash与提交一致；M1接受62文件bytes/mode与提交一致。本轮Git独立导出+新分析器：M0专用87、M1完整110后端+fixture1/35前端/7真实Chromium通过，零Skip。不能用历史PASS代替当前运行。
4. 已建M0 PR#1（M0→main）与M1 PR#2（M1→M0），二次查询open/mergeable true/merged false。M0正式合入后才retarget M1→main；GitHub测试merge SHA不是正式合并。本轮禁止自动合并。
5. 技术规范仅新任务architecture/acceptance/decisions/research-evidence/research_probe五文件，manifest raw SHA256 3e546ddd151ba17df2500ed930e0e2149f1ea314680651efc7124b7d075deb1b，绑定62源码。readonly original/copy/fixed docs结束身份均一致；README/导航/审核归档不是新增设计合同。v1留本地，v1-to-v2.patch可反向重建原3文件hash。
6. M2-A：sealed保存字节向量、base_git_head/represented_git_commit区分、原虚拟路径/最小冻结头文件视图、单schema4完整快照+workspace/attempt表/CAS事务、显式新路径legacy导入、protocol3定义/site证据、保守Diff、共享有界CLI/HTTP/两版本UI。A1–A6次序及22组oracle见任务；A只全量，不做reuse/Watcher。
7. M2-B：A独立通过后B1–B3 per-TU原始artifact、namespace结构变化全失效/内容read-set失效、安全复用后完整重聚合、强制full shadow对照/不一致回退。profile和toolchain/volatile builtin/metadata纳入键；不宣称当前已增量或加速。
8. Claude仍原UUID06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6，用户新指定claude-opus-5/high/auto，真实probe/init/argv确认。先独立稿（未读Codex），再2轮完整审核：round1 ACCEPT但not ready，round2 ACCEPT/ready。原稿/对比/裁决原样归档；单库/封存后host修改两处误述已由Claude在round2纠正。
9. round1一次Write格式空白死循环监督SIGINT，exit0但native is_error/无裁决，恢复同候选仅移除JSONSchema约束，auto未关。round2初次记录只显示4语义Read，监督补读第5脚本并末次独立hash，Claude自行更正/再次确认。原始流/失败/前补核文本仅本地，不能把无裁决attempt计PASS。
10. 本轮owned真实CLI五探针+两个Bwrap挂载/最小header视图可行性探针PASS，generic复现新目录再PASS；不证明M2 capture/protocol3/Diff已实现。R0报告只按风险论证，未来descriptor/alias/negative include/crash/site ambiguity是必过实施测试。
11. 本地m2-workspace-architecture-20261020含Git副本、新构建/DB/fixtures、所有argv/exit/logs、模型原始流、review-gate及Git交付证据。大日志/原始推理不入Git；旧资料archives/codeweave/m0,m1路径见archives/layout.json。Python.venv/LLVM18 resource lib/clang/18/Node22应现查。
12. 本轮只DevFlower新任务及必要导航，按授权同候选通过后Commit+Push project/codeweave；明确文件暂存、正常推送+远端SHA核验，不force/reset/clean，不把项目分支并回DevFlower main。源码/工作流SHA和用户验收/独立审核/Git交付分别报告。
