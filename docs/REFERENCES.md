# 来源与取舍

本文件记录方法借鉴，不声明已安装或依赖第三方框架。不拷贝其实现、整套提示词或技能文件。

## 来自既有实践

主要依据：[AI_MC_WW_interation 的 AGENTS](https://github.com/Silver-Zhang/AI_MC_WW_interation/blob/7f745e14688354caa1f8eb262d35d678af4f1554/AGENTS.md)、[任务工作流](https://github.com/Silver-Zhang/AI_MC_WW_interation/blob/7f745e14688354caa1f8eb262d35d678af4f1554/MLVR_develop/README.md) 与该版本的提交记录。

继承 A/B/C、五步关口、真实对话、证据/边界、独立复核、按需上下文及精简归档。改进点：不把特定科学项目规则固化到通用主线；任务状态单一来源；不要求一任务只能一个提交；完整区分 staged/unstaged/untracked；迁移不改历史。

## 公开方案

| 来源 | 借鉴 | 不整体采用 |
|---|---|---|
| [github/spec-kit](https://github.com/github/spec-kit) | 先明确需求与验收，再实施；共同原则与功能任务分层 | 不为小改强制生成整套 spec/plan/research 文档 |
| [obra/superpowers](https://github.com/obra/superpowers) | 完成前实际验证；实现与审核区分；隔离工作目录 | 不强制每个微任务启用子 Agent，不自动授予提交/清理权限 |
| [Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec) | 对存量工程按变更组织；当前规则与历史变更分开 | 不把勾完任务或归档动作等同于验收通过 |
| [humanlayer/12-factor-agents](https://github.com/humanlayer/12-factor-agents) | 主动控制上下文和执行流程，按需载入相关证据 | 它是 Agent 工程原则，不是项目治理软件；不引入运行时编排依赖 |

调研阅读的是当次公开页面，不据星数或宣传认定适用性。DevFlower 保留自己的权限、公开边界和有界验证规范。许可证仍各自有效；后续实际复制代码前须另外核对许可与归属。
