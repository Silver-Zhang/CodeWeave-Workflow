# Issue16 接续

任务20261024_02_issue16-model-session-routing，run396d0ad7c4644a26bb6c70812dc3ef39；完整合同见本机archives/devflower-issue16-20261024/contract.json（含Sim F）。源码development/issue16-experience，flow/model-session-routing，HEAD 89203371f2457bca54998e041de4c9f1c4ea804d，tree fa31992832bdfb047e9fcf393313babee681e2e6，163文件SHA256 767cb7fc599473f1715d9c903e7d2e6aa9089658063c731709ee7054ef5d4560。PR17 Draft依赖PR15；main e35dec1，Stable5816不可覆盖。

505Python/6host/151browser/18JS等最终回归全部0，证据regression/candidate-9。真实ae81候选四场景通过仅历史；最终同候选完整Codex/Claude场景尚未通过。R1原始NEEDS_CORRECTION保留，修复/补证待独立关闭；R2真实402无裁决；固定Gate最终BLOCKED，没有正向放行。不得改写旧失败/冒充硬ACCEPT。

先核验是否余额恢复，再跑当前候选真实模型流程并冻结新证据；最多5轮源码尝试，本任务已R1/R2，最多剩3轮。基础设施安全重试最多2次，不反复重试明确402。Claude深度deepseek-flash[1m]/high，物理后端/生效effort unknown；Codex gpt-6.1-sol/xhigh。不换模型或复制全局认证。

明确Claude SID19e82b7a-d457-4b61-b6a3-1dc0dea84d2b，HOME archives/devflower-issue16-20261024/runtime/r1，cwd /home/workspace/DevFlower，原生位置HOME/.claude/projects/-home-workspace-DevFlower/<SID>.jsonl。固定外部监督器helpers/review.py可--resume-from r2 --name r3 --stable-gate-round 3；先重建最终同候选evidence再用，不能--last或让待审Controller自批。

本机入口python3 /home/workspace/DevFlower/.local/open-issue16-workbench.py。源码允许正常开发PR提交推送，禁止合并main/晋升Stable/force/reset/clean/删除会话；用户个人UX仍待确认。task README为结论入口，evidence.json/manifest/R1原始结构化裁决为必要机器记录，原始大日志/截图/原生HOME只留本地。
