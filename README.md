# 通用研发工作流 · CodeWeave-Workflow

这是**可复用的多项目开发工作流仓库**，与任一软件源码仓库独立。它记录开发任务、方案、决策、有限的验证证据以及源码版本关联，不是 CodeWeave 的运行依赖，也不是代码地图知识库。

灵感来源：本账号 [AI_MC_WW_interation](https://github.com/Silver-Zhang/AI_MC_WW_interation) 的 MLVR_develop 任务制实践；已去除 RMC 和核物理专属规则。

## 快速入口

- [WORKFLOW.md](WORKFLOW.md)：A/B/C 模式、五步流程、审核关口、归档和提交边界。
- [AGENTS.md](AGENTS.md)：Codex、Claude 等 Agent 的简短硬规则。
- [STATUS.md](STATUS.md)：所有项目的一屏状态与待决策事项。
- [projects/](projects/)：每个项目独立维护 PROJECT、INDEX、plans 和逐任务档案。
- [templates/TASK.md](templates/TASK.md)：统一五节任务模板。
- [tools/new_task.py](tools/new_task.py)：创建任务档案并登记到项目 INDEX。
- [tools/check_archives.py](tools/check_archives.py)：只读归档一致性检查。

## 适用范围

可以同时管理 CodeWeave、其他科研软件和工程项目，各代码仓库仍分别管理 Git 提交。工作流仓库仅以项目配置、路径和**真实 Commit SHA** 关联源码，不把源码本体或运行缓存复制过来。

## Git 仓库边界

工作空间可以并列放置多个独立 Git 仓库；无需 Git submodule，更不应为工作空间顶层再创建混合仓库。任何项目可以采用自己的语言、构建系统和 CI。

**本仓库当前为 Public。** 禁止提交令牌、密码、私有源码摘录、含敏感数据的原始日志或真实内部路径；需要保留的原始证据放本地受控空间，只登记安全摘要和可复现方式。软件源码仓库不得依赖本仓库才能构建或运行。

当前已登记项目：[CodeWeave](projects/CodeWeave/PROJECT.md)。
