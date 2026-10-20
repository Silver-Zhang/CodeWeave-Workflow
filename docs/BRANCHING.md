# 分支、同步与历史保留

## 生命周期与人工 Gate

main 是唯一正式通用基线；长期分支仅 main 与 project/<slug>（包括 project/devflower、project/codeweave）。flow/work/refactor 分支可用于开发和 PR，不作为额外正式主线。项目分支整体不能合入 main。

PR 的远端 HEAD/tree 必须对应当前通过必需验证、独立 ACCEPT、旧阻断项关闭的候选。先审查相对 main 的全部差异，确认仅通用框架、无 project 实例/原始日志/凭据/未审代码，报告 READY_TO_MERGE；该状态不是合并授权。人明确批准后才按批准方式合并，读回 main 实际 HEAD，在正式 main 重跑基础回归与 check --baseline，并记录历史继承关系。

临时远端分支仅在合并/历史保留确认且另获明确删除授权后清理，不删除 project 分支、不 force-push。主线合并、源码推送与分支清理是不同权限；已有任务许可不是未来所有任务的永久许可。

## 文件边界

通用主线保留根规则、`docs/`、`templates/`、`tools/`、`tests/`。项目分支仅增加 `project/`：PROJECT.md、project.json、STATUS.md、AGENT_CONTEXT.md、INDEX.md、plans/、tasks/。项目专属规则不要改写根 AGENTS/WORKFLOW；确需试验共同规则时使用独立提交便于提炼。

## 通用升级 → 项目

在干净的项目工作目录先检查当前分支、差异和远端。经授权获取 main 的新版本，在 `project/<slug>` 上 merge 该版本，审查规则冲突并跑测试、`check`。更新 `project/project.json` 中采用的 framework_base 为实际 main SHA。普通 merge 不重写项目历史。

## 项目经验 → 通用主线

从 main 新建 `flow/<topic>`，重写为通用补丁或选择一个只含通用路径的提交；预检文件列表，排除 `project/`、旧 `projects/` 及私有输入。跑 `check --baseline` 与测试，提 PR 到 main。项目整个分支不能回并主线；也不要 cherry-pick 混有项目记录的提交。

## 本次迁移

现有 `projects/<name>/` 内容应先保存在项目分支，再迁至 `project/`；计划与历史报告原文保留，修正仅通过单独迁移说明，不能回写历史使它看起来用了新流程。main 的旧历史继续保留，因此历史中曾公开的数据不会因删除当前文件而变私有。

本次工作分支 `refactor/devflower-baseline` 提供通用候选；`project/codeweave` 保留并适配既有实例。候选经审阅合并 main 后才成为默认通用基线；不要创建 project 分支到 main 的合并请求。

## 并行目录与权限

一个物理目录只服务一个活动项目。多个项目可以独立 clone 同一 repo 的不同分支，或经授权使用 git worktree。切换 Git 分支不会自动清除不跟踪的日志；不要在相同目录来回切项目。不要自动删除旧 worktree/日志。

仓库公开则所有分支、历史均公开；项目分支不是权限隔离。如需私有记录，应另设私有仓库或把整个工作流仓库改为 Private，不能只“隐藏分支”。更名不会改变此边界。远端改名后先核对仓库数字 ID，再更新 remote URL；不要创建同名新仓库替代现有历史。
