# CodeWeave 接手上下文

1. 先读 STATUS.md，再读 PROJECT.md 与当前任务 §1/§3/§4。
2. 已确认：独立 Public/MIT 源码仓库；地图同时供人类与 Agent 使用，不是知识库。
3. 首版：C++/Clang → 结构索引 → CLI/HTTP → Web；已保存工作区与 Git 版本均需绑定源码身份。
4. 源码基线核验记录为 676f63d4；不能据旧 SHA 假装当前工作区已检查。
5. 共用规则来源以 project.json 的 framework_base 为准，目前是待合并候选。
6. 下个目标是 M0 多编译单元源码定位闭环，不是 GitLab、聊天或复杂全程序时序。
7. 只读 RMC，不改核数据、reference、冻结设计；不把内部代码公开。
8. 历史初始化报告保持原文，其测试说明不能替代新 checkout 的实际测试。
9. 新会话不通读全部 tasks；按 INDEX 定位后再展开。
