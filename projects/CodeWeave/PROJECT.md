# CodeWeave 项目配置

| 项 | 值 |
|---|---|
| 独立源码仓库 | [Silver-Zhang/CodeWeave](https://github.com/Silver-Zhang/CodeWeave) |
| 开发形式 | Linux 本地源码 + Web UI + CLI（Agent 查询） |
| 默认工作模式 | B · 工程协作 |
| 当前冻结目标 | [Base v0.1](plans/BASE_v0.1.md) |
| 任务台账 | [INDEX.md](INDEX.md) |

## 已确定边界

产品是代码结构地图，不是 Markdown 笔记或聊天记忆库。人类前端与 Agent CLI 共用同一索引；源码导入保持只读。首版覆盖保存后的本地工作区修改和 Git 双提交结构差异；静态图不冒充真实时序。AI 解释、GitLab 集成和运行时 Trace 不属于初版。

RMC 可以作为后续真实验证项目，但其生产源码、核数据库、reference 和 F11 冻结结果**不得被 CodeWeave 修改**。不用 RMC 代码作为公开测试素材。

工作流记录不应出现在 CodeWeave 源码仓库，也不作为运行依赖。
