# devflower 项目约定

仅在 project/devflower 分支生效，共同规则见 ../AGENTS.md 与 ../WORKFLOW.md。

- 默认 B 模式；权限以当次用户授权为准。
- 框架 Git 主仓库为 /home/workspace/DevFlower/DevFlower；源码开发在 /home/workspace/DevFlower/development 下使用从已核验 main 派生的独立 flow 工作树，当次分支见 STATUS.md。project/devflower 通过 /home/workspace/DevFlower/records 同仓库独立工作树保存项目档案，不把框架实现放进记录变更。
- 任务记录集中在 project/tasks/<month>/<task>/：一份五节 README、task.json、必要机器证据；INDEX 自动生成。
- 本地过程、原始日志、候选、构建物与专用运行目录统一放/home/workspace/DevFlower/archives/<task>/，不散落工作区或源码根目录。认证/会话不上传。
- 历史记录保留当时的路径与结论；搬移另记映射和完整性核对，不重写原始裁决。
- CodeWeave 的历史过程材料仅按项目归档；其源码及 project/codeweave 档案不在本任务修改范围。
- PR 合并、真实业务试点、未来自动交付分别授权；实现完成不等于用户验收或已进入 main。
