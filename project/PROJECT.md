# CodeWeave 项目约定

本项目实例位于 DevFlower 的 `project/codeweave` 分支；共同工作流见 ../AGENTS.md 与 ../WORKFLOW.md。

| 项 | 当前约定 |
|---|---|
| 源码仓库 | https://github.com/Silver-Zhang/CodeWeave |
| 上次核验的源码 main | 676f63d4c8d14f23e263f43e828deae566a9b9ec（开工前重新核验） |
| 产品基线 | [BASE_v0.1](plans/BASE_v0.1.md) |
| 默认模式 | B · 工程协作 |
| 当前关口 | 通用工作流重构候选待审；M0 尚未实施 |

产品是自动提取的代码结构地图，不是聊天记录或 Markdown 知识库。人类 Web 界面和外部 Agent 查询共用同一索引；本地保存后的修改和 Git 双版本结构差异属于首版目标。聊天 Agent、GitLab 集成、运行时序后置。

目标仓库是只读分析对象。RMC 仅作为后续授权的实际验证项目，生产源码、数据库、reference 和 F11 冻结结果不修改；RMC 片段不进入公开 fixtures。

本地工作空间将 CodeWeave 源码与 DevFlower 项目 clone 并列放置，顶层不初始化混合 Git 仓库。工作流和方案不是 CodeWeave 构建、测试或运行的依赖。
