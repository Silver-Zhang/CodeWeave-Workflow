# CodeWeave · Base v0.1 产品与技术基线

**状态：目标和范围确认；核心能力尚未实施。**

## 产品定位

自动分析大型 C++ Git 仓库，生成可查询、可交互并随源码变化更新的结构地图。人和 Agent 使用相同的结构索引；减少探索性全文阅读，直接定位类、函数、调用点和相关源码。

本产品不是聊天记忆库，不预设人工维护 Markdown，静态关系不等于运行事实。

## 首版能力

- C++ 文件/命名空间/类/函数实体、包含/继承/调用等静态关系、调用点与定义的精确位置；
- 编译数据库、编译配置、源码快照和分析覆盖元信息；
- 以函数为中心分层展开、搜索、筛选、源码定位；不一次性渲染全图；
- CLI/HTTP 结构查询：overview、find_symbol、symbol、neighbors、paths、source、diff、status；
- 保存后的本地工作区更新（含新增/删除文件）、HEAD ↔ 工作区、Commit A ↔ Commit B；
- 静态解析未知或失败时明确标记，不把缺失推断为删除。

## 技术方向

Clang LibTooling C++ 提取器；Python/FastAPI + SQLite；React/TypeScript/Vite；React Flow + ELKjs；Monaco；Git 私有缓存快照。AI/LLM 不应成为基本地图功能的依赖。先技术实测，再锁定具体包版本。

## 实施里程碑

| M0 | 用自有多文件 C++ Fixtures 打通 Clang → SQLite → CLI；验证重载、跨文件调用与代码锚点。 |
| M1 | 真实索引驱动的网页地图，检索、局部展开、源码导航，与 CLI 结果一致。 |
| M2 | 已保存工作区变化与增量失效、HEAD ↔ 工作区对照。 |
| M3 | Commit 双版本对照、函数和调用边差异、真实 RMC 只读适配验证。 |

M0 开发另立任务并经授权；当前没有完整 Clang 索引器、Graph UI 或 Git Diff 实现。时序、状态生命周期、地图内 Agent 聊天和 GitLab 集成均后置。
