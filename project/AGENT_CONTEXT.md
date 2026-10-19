# 接手入口

DevFlower 自身工作区 /home/workspace/DevFlower。唯一开发仓库 DevFlower/，flow/multi-agent-orchestration，当前 2e298e4；同仓库 project/devflower 记录工作树为 records/，自身项目档案就在 records/project/。原始证据为 archives/v0.2-a-final-integration/evidence/。

当前任务 20261019_02_v02a-final-integration，按需读任务 README §1/§3/§4 和 evidence.json。已具备 READY_TO_MERGE：89+4 自验、46+46 独立/外部检查、真实当前 CLI 修复闭环及框架 ACCEPT。主线仍 536a058、PR #2 待人工合并；main 合并和临时分支删除分别等待明确授权，禁止用旧任务授权覆盖未来业务交付。

Controller 的 doctor/run 等命令从源码 DevFlower/tools/devflower.py 执行；记录的 init/new/index/check 在 records 工作树执行。该记录分支只写项目档案，不把框架实现或大日志混入。

CodeWeave_dev 的 CodeWeave 是业务源码，DevFlower 是其 project/codeweave 工作流实例，12 份任务记录必须保留；不要在其中开发本框架。历史原始路径/授权/会话记录不改写；迁移回执在 archives/workspace-migrations/。模型路由和 effort 保持用户当前批准配置，缺失实际字段仍写 unknown。
