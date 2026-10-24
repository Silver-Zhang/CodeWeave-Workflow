# PR15/PR17 最终集成接续

当前任务 `tasks/2026-10/20261024_03_pr15-pr17-final-integration`；run7120c8604d44468eb353931ac0cbb384。先读本任务README/validation.json。原任务02和Issue14原始报告不得改写或续预算。

独立源码目录 development/final-pr15（flow/pr15-final-correction）和 development/final-workbench（flow/pr15-pr17-final-validation），正常FF推向远端flow/workbench-ux-polish与flow/model-session-routing。原issue14-ux、issue16-experience工作树及用户页面保持原样，不擅自同步覆盖。

PR15 HEAD546cba4ec92390eeef2218e119647485ee358ce1/tree c0b01275df195a2e74668442b82a93264c14ba3c/154文件CF302125c7e87ff5f7bb4e6bcc57ac38ae0ecb375ac445d22410a5adc7ab9f28c9。PR17 HEADa3b22f37e7e23f11fbc23d9e613e1662d91a17ec/tree6c873146e04a3c820213e179a24931e9ba5e21df/173文件CF0d1869aa19b15629fc0de6e68668fc8815a10505a77d214fd8a5662835f265a5，完整继承PR15。

478/517 Python、6host各、142/161browser、18/20JS均exit0、FAIL/ERROR/SKIP0，Baseline/语法/字节一致构建通过。PR15新R4原始硬ACCEPT，外部固定旧Stable Gate ACCEPT；R4监督脚本元数据覆盖错误原件保留，session-recovered.json为追加身份恢复，无新请求/裁决改写。PR17新R5最终NEEDS_CORRECTION，I16-A FAIL，其余22合同PASS；OPEN P1 I16-A-MODEL-ADMISSION：新鲜成功目录省略默认模型，model_catalog仍追加可执行项，node_binding仍准入。原样独立反例由受控runner复现，script0仅指反例完成，行为1项FAIL；固定旧Gate BLOCKED/exit2。五轮源码预算及两次基础设施恢复全部耗尽，任务停止，不隐式第六轮。两次安全探测已用完，各1请求，第二次明确同HOME/UUID恢复。不无限重试/模型改判。

本任务Claude claude-opus-5-5[1m]/high；Codex gpt-6.1-sol/xhigh。实际模型回报与物理后端/有效effort分开，后两者unknown。原生HOME/cwd/UUID/记录路径见validation.json，日志和会话不复制到Git，不使用--last。

可信固定Gate仅 stable/usable-v1-5816ba4776b3（源码5816ba4776b35d625e163af805d656315a7c638ba4e60e576763b121d86b3821；Gate12f0b6aaf8d257e1ce0b87346e2f328089ab28fc96c52691719b7f28787630ab）。新Controller不能自批。用户本轮条件式合并许可须两候选硬ACCEPT+固定Gate+集成复核；不把PR15结论套PR17，Stable审批独立，预算耗尽保持Draft。

Development入口 python3 /home/workspace/DevFlower/.local/open-pr15-pr17-workbench.py，已验证http35557/CF0d1869；launcher不输出私有fragment，活动会话/终端未核验时不重启。旧入口/Stable5816保持。用户UX未验收；原始证据仅archives/devflower-pr15-pr17-final-20261024。

下一任务最小范围：统一模型目录/新会话/节点启动准入，缺失默认项只可待核验或另取等效原生验证，不把配置登记当作实时可用证明；保留当前负面报告、新建明确授权及预算，不续旧运行。两个PR保持Draft，main未合并。
