# DevFlower Studio 0.1

可运行的本地 Web 画布，不是 n8n 的 fork。独立 Python 标准库服务 + 原生 HTML/CSS/JavaScript/SVG，无 npm 构建、CDN、字体下载或第三方运行依赖。Controller 以最小增量记录验证操作身份和候选轮次；A/B/C、五阶段流程、Controller 授权与 Git 门禁保持原状。

## 1. 启动

在包含 v0.2-A 的 DevFlower checkout 中，需要 Python 3.11+：

```sh
python3 tools/devflower_studio.py --workspace "$HOME/.local/share/devflower-studio-preview"
```

`--workspace` 首次必须是**尚不存在**的新目录，不能在框架源码或 Controller 控制目录内部，也不能包含它们。以后复用同一个 Studio 目录即可加载已保存版本。此目录存 Studio 草稿与可重建的最小会话索引，不替代 project 分支、task.json 或运行状态库。

打开终端打印的完整地址，形如 `http://127.0.0.1:8765/#token=...`。令牌仅保存在当前浏览器会话，页面读取后清除地址栏的 fragment。不要分享令牌。服务仅监听 127.0.0.1，不用于多用户公网部署。端口冲突可用 `--port 8766`。

远程服务器使用同端口 SSH 转发，不向公网开放监听地址：

```sh
ssh -N -L 8765:127.0.0.1:8765 your-user@your-server
```

在本地浏览器打开服务器终端给出的地址。前后两端端口应一致，否则严格 Host 校验会拒绝访问。

## 2. 真正能编辑什么

左侧选择已保存版本或新建 B 模式模板。中央拖动节点、平移画布、缩放；选择节点在右侧编辑名称、模型、推理强度或验证命令。支持撤销/重做、JSON 导入导出、版本保存与跨标签页冲突检测。

执行语法刻意限定为当前 Engine 已支持的范围：

```text
授权 → Codex → 冻结候选 → 一个或多个顺序验证 → Claude Code → Gate → 交付
          ↑                                              │
          └──────────────── 有界修复 ─────────────────────┘
```

可以增加测试节点、调整验证顺序、修改参数；从模块出口拖到另一个模块入口连接，也可点击出口再点击入口。选择连线后可删除。只有满足执行语法的图才能保存或导出任务，孤立节点、并行分支、任意循环、缺少修复边或越过门禁的边均被后端拒绝。固定环节不能删除，既有任务的必需验证 ID 不能悄悄移除。编辑器支持 1–20 项验证和 ASCII 字母/数字/`_.-` ID（首位字母或数字，最多 80 字符）；超出此子集的导入明确拒绝，不截断任务。只读监控保留实际全部验证节点。

**坐标是布局；验证顺序、goal、model/effort 和 limits 会真正编译到任务配置。** 本版不是任意图执行器；不支持额外并行 Agent、任意条件节点、子工作流或 C 模式 G1–G4 的程序化调度。A/C 原有人工工作流继续使用，导入它们不会自动转换为 B。

## 3. 从画布生成真实任务

先用原有任务准备方式取得完整 B 模式 `task.json`。它包含 source、acceptance、scope、bindings、policy 等；不要导入 `operator.json`、认证文件或会话全文。

1. 点击“导入任务”，画布按照任务中的实际验证顺序生成。
2. 编辑目标、模型、测试和预算，校验并保存画布版本。
3. 点击“导出任务配置”，得到 `task.studio.json`。原任务的源码范围、会话绑定、必需合同及 delivery 权限保留；原任务文件不被改写。
4. 按既有流程，由真实操作员核对并生成/更新匹配这份配置的授权。画布从不签发授权。
5. 在终端启动现有 Controller：

```sh
python3 tools/devflower.py run --control /absolute/control \
  --config /absolute/task.studio.json --authorization /absolute/operator.json
```

导出的配置经过现有 `config_check()` 验证。`config_sha256` 使用与 Controller 一致的规范 JSON 哈希；改动执行参数后旧授权不再匹配。导出成功不是授权、测试通过或 ACCEPT。

保存的 Studio 版本只包含画布，不保存完整任务配置、凭据和授权。重新加载画布后，可在右侧点“绑定 task.json（保留此画布）”，再导出配置。“导入任务”则从任务重新建立画布。

## 4. 看实际进度

```sh
python3 tools/devflower_studio.py \
  --workspace "$HOME/.local/share/devflower-studio-preview" \
  --control /absolute/control
```

选择左侧真实运行，进入“运行监控”。每秒读取 Controller 的 `runs/events/operations`；每次查询在同一个只读 SQLite 事务中取得一致快照，支持读取正在更新的 WAL，不使用会漏掉新事务的 `immutable=1`。缺库不会创建假运行或数据库。

验证节点按运行、轮次、验证 ID 与操作 ID 关联，区分未开始、运行中、已执行待结果验证、通过、失败和阻断。退出码 0 不等于通过；计数和结论来自 Controller 的结果校验。相同命令的不同验证不会混淆。新轮次冻结前，旧候选单列为 previous_candidate；旧审核和测试不作为本轮证据。旧版本缺少候选轮次时标为未归属，不猜测。

运行视图从**实际运行的 config**生成，不能用编辑中的草稿冒充本次执行。显示 Controller 状态、当前轮次、测试计数、当前候选、真实裁决、最近最多 200 条事件、最近审核轮次及交付收据。不显示原始 argv、prompt、授权、会话全文、隐藏推理、原始 stdout/stderr 或任意 artifact 文件。

只有 host、boot ID、PID/start identity 与本机活进程匹配，才显示“进程运行中”。外机、过期记录或无法确认进程都显示“未证实”；数据库的 RUNNING 字符串不自动变成绿色活跃状态。快照请求绑定所选 run_id 和请求版本；切换运行立即清空旧快照，迟到响应和旧请求失败不会覆盖新选择。标题、节点、轮次和审核信息来自同一份已核对身份的快照。断线会清空过期节点与裁决并明确降级，不继续播放活跃连线。事件日志是阶段记录，不是模型思考或 token 流；UI 不猜测完成百分比。

`READY`、`LOCAL_COMMITTED`、`PARTIAL_DELIVERY`、`CANCELLED` 含义与 Engine 一致。界面没有 resume/cancel/deliver/merge/授权写入端点；这些仍由现有 CLI 和真实用户 Gate 处理。

## 5. 可选：从画布启动已授权任务

默认关闭。需要操作员在启动 Studio 时明确绑定**同一份**任务与授权：

```sh
python3 tools/devflower_studio.py \
  --workspace "$HOME/.local/share/devflower-studio-preview" \
  --control /absolute/control \
  --launch-task /absolute/task.studio.json \
  --authorization /absolute/operator.json
```

浏览器导入这份任务并导出校验后，只有编译得到的 config hash 与终端绑定完全一致，按钮才启用。每次输入、导入、新建和加载都会使旧编译失效；编译绑定完整文档/任务快照及请求版本，丢弃过期或逆序返回的结果。启动前重新核对画布、编译快照及操作员绑定。后端再次核验文件、授权和 Engine `authorized()`。客户端不能传路径、shell 或任意命令。每个服务实例只允许一次启动；已有同配置的未终结运行会阻止盲目重复。失败后先检查记录，不自动重试。

这只调用固定的 `tools/devflower.py run`，并不赋予 Git 交付能力。Controller 的目标、授权、隔离、锁、验证和自举规则仍然生效。启动回执不是成功证明，最终以状态库为准。关闭 Studio/浏览器不会取消已经明确启动的 Controller；需要停止时用原 CLI 的 cancel。UI 不管理主线合并。

## 6. 安全与版本边界

服务使用每次启动随机令牌、严格 Host/Origin/Fetch-Metadata 校验、无 CORS、CSP 和请求大小上限。API 错误不返回 Engine 异常正文、凭据或任意文件内容。读取 Controller 时不执行 SQL 写入；SQLite 的 WAL 读锁/共享内存机制不等于修改工作流权威状态。Studio 的草稿 SQLite 保存不可变画布版本；另有独立的最小会话索引，乐观并发失败返回 409，不覆盖另一标签页的修改。保存绑定发起时的草稿身份、版本和文档快照；同一草稿的保存串行，切换或新建后旧响应只刷新历史，不改变当前草稿身份。保存期间继续编辑仍显示未保存改动。

这是单人、本地开发工具，不是面对不可信本机账户、恶意管理员或公网的完整隔离边界。不要在节点目标、标签或命令中输入凭据。私有源码外发依然须独立授权。前端不收集遥测。

## 7. 验证

```sh
python3 -m unittest discover -s tests -p test_studio.py -v
node --check tools/studio/static/app.js
# 定向竞态测试：真实 HTTP；启动状态使用显式夹具，不调用模型
python3 tests/studio_races.py --chromium /usr/bin/chromium --artifacts /tmp/studio-races
# 保存和监控身份竞态：真实 HTTP + SQLite 夹具，无模型调用
python3 tests/studio_identity_races.py --chromium /usr/bin/chromium --artifacts /tmp/studio-identity-races
# 可选浏览器测试（另行安装 Playwright 和可用 Chromium）：
python3 tests/studio_browser.py --chromium /usr/bin/chromium
```

初版交付记录（a93ed81，以下限制属于当时证据）：

本次实现环境：Python 3.13.5、Node 22.16.0。新增 35 项单元/HTTP/SQLite/编译测试通过；16 项 Chromium 交互检查通过，包括拖拽、导入、保存、导出、WAL 更新、旧进程、断线和只读画布。

**证据边界：**容器不能解析 GitHub，未取得完整 checkout；实际读取远端固定版本并重建本轮测试依赖，`common.py`、`contracts.py` 和 policy Schema 与 Git blob SHA 一致。没有重跑旧的 89 项核心回归。容器 Chromium 禁止直接 HTTP 导航，交互检查采用 `--offline-bridge`：页面执行真实 JS，API 经 Python 桥接到真实本地 HTTP 服务；不宣称完成普通浏览器网络通道的端到端测试。新 CI 只运行 Studio 合同与 JS 语法测试。

本轮没有调用真实 Codex/Claude 服务；启动监督测试中的 Popen/authorization 是明确标注的模拟。读取进度使用当前 SQLite 合同的测试夹具，不冒充模型运行。新增独立 Claude 源码审核、用户实际任务试用和主线验收待完成。此版本先以开发分支/PR 交付，不自动合并 main。

## 8. Workspace Manager M0：业务工作区与原生会话

`--workspace` 仍然是 Studio 专有草稿和索引目录。业务源码目录另用
`--project-root` 登记，可重复指定（最多 8 个）：

```sh
python3 tools/devflower_studio.py \
  --workspace /absolute/new-studio-data \
  --project-root /home/A --project-root /home/B \
  --session-profiles /absolute/operator/session-profiles.json
```

左侧和“Agent 会话（只读）”面板可以切换已登记工作区。显示规范化路径、
本机身份、各来源扫描覆盖、Provider/Profile/原生 ID、记录中的 cwd、
时间、CLI 版本和能力。切换、关闭、并发刷新及网络错误会使旧响应失效；
不复用 Controller 运行画布或任务裁决。浏览器没有原生目录选择器，
也不能登记任意路径、写入会话、启动模型或执行恢复命令。

不提供登记文件时，扫描当前 `HOME/.codex/sessions`（或 `CODEX_HOME/sessions`）、
`HOME/.claude/projects`（或 `CLAUDE_CONFIG_DIR/projects`），以及每个业务工作区
**直接**包含的 `.codex/sessions`、`.claude/projects`。不会递归搜索整个 HOME
或项目源码寻找历史库；更深的嵌套根和独立审核 HOME 必须明确登记。
只有原生会话结构和元数据匹配才生成索引行，单独的项目配置目录不算会话库。

登记文件是操作员在终端选择的本地 JSON，不是浏览器输入：

```json
{
  "defaults": true,
  "limits": {"depth": 5, "entries": 2000, "files": 200, "bytes": 33554432},
  "profiles": [
    {
      "provider": "claude",
      "home": "/absolute/reviewer-home",
      "config_root": "/absolute/reviewer-home/.claude",
      "workspace": "/home/A",
      "original_project_root": "/home/A"
    },
    {
      "provider": "codex",
      "home": "/home/operator",
      "config_root": "/home/operator/.codex",
      "workspace": "/home/A",
      "original_project_root": "/old/project-A",
      "session_ids": ["11111111-2222-4333-8444-555555555555"]
    }
  ]
}
```

`workspace` 与 `original_project_root` 必须成对出现，前者必须已用
`--project-root` 登记。共享旧 cwd 时使用明确的 `session_ids` 限定原生 UUID，
避免把整个存储环境的其他项目误归属。不同 Provider、环境、原始文件的相同 ID
不会静默合并。cwd 与登记原属不符、目录不存在、会话中 cwd 改变，都会明确降级。
目录“已核验”只表示记录中的路径当前可访问，不证明对应进程仍运行。

`home` 是原启动环境，不能从会话 cwd 猜测。Claude 支持可选的
`settings_file`，用于原 CLI 的显式 `--settings` 绑定；索引器不读取其内容。
直接发现的嵌套库没有可靠 HOME 时，不生成恢复命令。
恢复建议固定原 HOME、CODEX_HOME/CLAUDE_CONFIG_DIR、cwd 和明确 UUID，
使用 shell 参数转义，只能查看或复制。**本版发现器不调用原生 CLI 恢复，
不把元数据或登记声明当作原生成功证据；当前恢复能力一律标未验证，
不会显示“可恢复”。** 版本兼容、进程占用与认证也不从文件存在推断；
登记不会让会话自动出现在提供方默认历史列表。

扫描每来源最多 2000 目录项、200 文件、32 MiB，总单文件不超过 16 MiB、
单行不超过 1 MiB、深度最多 5。操作员可降低这些预算；超限、不可读、
损坏/部分 JSONL、变化中的文件、符号链接和未知布局均明确报告覆盖缺口，
不把部分扫描标为全面发现。Codex 支持已观测的 rollout JSONL 主元数据
及双 UUID 文件名；Claude 支持 projects 下主 UUID JSONL。
未知格式、子 Agent 私有布局和 Copilot 为未覆盖/unsupported，不猜测兼容性。

每级目录使用 `openat/O_NOFOLLOW`，拒绝跨符号链接及特殊文件，所有原生文件
只读打开。Studio 的 `sessions.sqlite` 仅存 Profile、工作区映射与允许字段的
最小索引，绝不保存消息正文、隐藏推理、认证内容或环境变量全集。
默认 API 只披露操作员登记范围内的路径；越界 cwd 隐去，疑似凭据的路径组件
打码，错误不回显原文件内容。原生目录与 Studio 数据目录必须分离；
索引可以独立删除重建，删除索引不会删除任何原生会话。

验证：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tests/workspace_browser.py --chromium /absolute/chrome --artifacts /tmp/new-workspace-browser
node --check tools/studio/static/workspace.js
```

浏览器测试使用合成原生会话和普通 HTTP；它们证明 UI/索引与只读边界，
不冒充真实模型或原生会话恢复成功。

扫描统计与读取共用同一份 inode/大小/mtime 快照；原始 IO 层也限制读取大小，避免缓冲预读突破预算。检测到增长或截断会拒绝该文件。Linux `O_PATH` 句柄先固定 inode 并验证普通文件类型，再通过 `/proc/self/fd` 为同一 inode 打开数据流；特殊文件只可能取得元数据句柄，不打开数据流。已发现的 FIFO/socket/device 作为 `special_file` 覆盖缺口报告，类型替换则拒绝为 `not_private_regular`。非法 Unicode 路径与无法解码的目录名按 `invalid_path` 隔离，其他有效会话仍可展示。此路径需要 Linux 的 `O_PATH` 与可用的 `/proc/self/fd`；不可用时失败封闭。
