# DevFlower

面向人类与 Agent 协作的轻量研发工作流。通用主线负责规则与工具，项目长期分支负责实际工作记录；源码保持独立仓库。

## 分支，而不是 main 下的多项目目录

| 分支 | 内容 | 合并方向 |
|---|---|---|
| `main` | 通用规则、模板、工具和测试；不含任何项目实例 | 接收经过提炼的通用改进 |
| `project/<slug>` | 通用文件 + `project/` 下单个项目的方案、进度、任务记录 | 接收 main；不整体合回 main |
| `work/<slug>/<task>` | 从对应项目分支创建的任务分支 | 回对应 project 分支 |
| `flow/<topic>` 或 `refactor/<topic>` | 从 main 派生的通用框架改进 | 经审阅回 main |

一个项目工作目录不要反复切换多个项目分支。并行项目用独立 clone 或经批准的 worktree，避免未跟踪文件串项目。详见 [分支与回流](docs/BRANCHING.md)。

## 入口

Agent 先读 [AGENTS.md](AGENTS.md)，存在项目实例时再读 `project/STATUS.md` 与 `project/AGENT_CONTEXT.md`；任务只按需读 §1/§3/§4。详细规则见 [WORKFLOW.md](WORKFLOW.md)。

需要在本机打开项目、配置工作流并驱动真实 Agent 时，见 [Stable Studio 使用说明](docs/USABLE.md)。原有画布和只读会话发现见 [Studio](docs/STUDIO.md)。

新的命名会话、React Flow 可执行画布与 v3 图协议见 [Development Agent 工作台](docs/WORKBENCH.md)。这是单独的开发预览，仍需完整验收和独立审核，不能替代当前可信 Stable。

## 开始一个项目

需要 Python 3.11+ 和 Git，无第三方 Python 依赖。先在干净的工作流 clone 中确认远端与基线，再创建 `project/<slug>` 分支：

```bash
git switch -c project/demo main
python3 tools/devflower.py init demo
python3 tools/devflower.py new parser-smoke --mode B
python3 tools/devflower.py check
```

`init` 只写当前工作流仓库的 `project/`，不创建/切换分支，不修改源码仓库，不提交或推送。`new` 创建一份五节 README 和一份小型 `task.json`；后者是任务模式与状态的唯一机器可读来源。编辑状态后运行 `python3 tools/devflower.py index` 更新台账；不要手工修改生成表。

```bash
python3 -m unittest discover -s tests -v
python3 tools/devflower.py check --baseline
```

`--baseline` 验证当前树中没有项目实例；普通 `check` 在项目分支检查任务与台账。检查通过不等于结果正确、用户验收或允许发布。

## 迁移与许可边界

Linux 本地双 Agent 运行器的实际接口、最小任务例、授权格式及限制见
[ORCHESTRATOR](docs/ORCHESTRATOR.md)。实施设计合同与 A01–A16 仍见
[v0.2-A](docs/design/v0.2-a/README.md)；设计文档不代替实际测试或独立验收。

现有项目记录先保留到项目分支，再从通用基线的当前树移除；不重写旧提交。物理仓库重命名由管理员执行，品牌名称不等于远端已改名。公开仓库的所有项目分支都公开，分支不提供权限隔离。

既有仓库许可证保持不变。Development 工作台直接使用 React Flow 等前端依赖，版本及第三方许可证见 [工作台说明](docs/WORKBENCH.md)；其余调研与取舍见 [REFERENCES](docs/REFERENCES.md)。
