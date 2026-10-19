# DevFlower Studio 0.1

可运行的本地 Web 画布，不是 n8n 的 fork。独立 Python 标准库服务 + 原生 HTML/CSS/JavaScript/SVG，无 npm 构建、CDN、字体下载或第三方运行依赖。Engine 的现有文件不修改；A/B/C、五阶段流程、Controller 授权与 Git 门禁保持原状。

## 1. 启动

在包含 v0.2-A 的 DevFlower checkout 中，需要 Python 3.11+：

```sh
python3 tools/devflower_studio.py --workspace "$HOME/.local/share/devflower-studio-preview"
```

`--workspace` 首次必须是**尚不存在**的新目录，不能在框架源码或 Controller 控制目录内部，也不能包含它们。以后复用同一个 Studio 目录即可加载已保存版本。此目录只存 Studio 草稿，不替代 project 分支、task.json 或运行状态库。

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

可以增加测试节点、调整验证顺序、修改参数；从模块出口拖到另一个模块入口连接，也可点击出口再点击入口。选择连线后可删除。只有满足执行语法的图才能保存或导出任务，孤立节点、并行分支、任意循环、缺少修复边或越过门禁的边均被后端拒绝。固定环节不能删除，既有任务的必需验证 ID 不能悄悄移除。

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

运行视图从**实际运行的 config**生成，不能用编辑中的草稿冒充本次执行。显示 Controller 状态、当前轮次、测试计数、当前候选、真实裁决、最近最多 200 条事件、最近审核轮次及交付收据。不显示原始 argv、prompt、授权、会话全文、隐藏推理、原始 stdout/stderr 或任意 artifact 文件。

只有 host、boot ID、PID/start identity 与本机活进程匹配，才显示“进程运行中”。外机、过期记录或无法确认进程都显示“未证实”；数据库的 RUNNING 字符串不自动变成绿色活跃状态。断线会明确降级，不继续播放活跃连线。事件日志是阶段记录，不是模型思考或 token 流；UI 不猜测完成百分比。

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

浏览器导入这份任务并导出校验后，只有编译得到的 config hash 与终端绑定完全一致，按钮才启用。启动前再次核验文件、授权和 Engine `authorized()`。客户端不能传路径、shell 或任意命令。每个服务实例只允许一次启动；已有同配置的未终结运行会阻止盲目重复。失败后先检查记录，不自动重试。

这只调用固定的 `tools/devflower.py run`，并不赋予 Git 交付能力。Controller 的目标、授权、隔离、锁、验证和自举规则仍然生效。启动回执不是成功证明，最终以状态库为准。关闭 Studio/浏览器不会取消已经明确启动的 Controller；需要停止时用原 CLI 的 cancel。UI 不管理主线合并。

## 6. 安全与版本边界

服务使用每次启动随机令牌、严格 Host/Origin/Fetch-Metadata 校验、无 CORS、CSP 和请求大小上限。API 错误不返回 Engine 异常正文、凭据或任意文件内容。读取 Controller 时不执行 SQL 写入；SQLite 的 WAL 读锁/共享内存机制不等于修改工作流权威状态。Studio 的独立 SQLite 只存不可变画布版本，乐观并发失败返回 409，不覆盖另一标签页的修改。

这是单人、本地开发工具，不是面对不可信本机账户、恶意管理员或公网的完整隔离边界。不要在节点目标、标签或命令中输入凭据。私有源码外发依然须独立授权。前端不收集遥测。

## 7. 验证

```sh
python3 -m unittest discover -s tests -p test_studio.py -v
node --check tools/studio/static/app.js
# 可选浏览器测试（另行安装 Playwright 和可用 Chromium）：
python3 tests/studio_browser.py --chromium /usr/bin/chromium
```

本次实现环境：Python 3.13.5、Node 22.16.0。新增 35 项单元/HTTP/SQLite/编译测试通过；16 项 Chromium 交互检查通过，包括拖拽、导入、保存、导出、WAL 更新、旧进程、断线和只读画布。

**证据边界：**容器不能解析 GitHub，未取得完整 checkout；实际读取远端固定版本并重建本轮测试依赖，`common.py`、`contracts.py` 和 policy Schema 与 Git blob SHA 一致。没有重跑旧的 89 项核心回归。容器 Chromium 禁止直接 HTTP 导航，交互检查采用 `--offline-bridge`：页面执行真实 JS，API 经 Python 桥接到真实本地 HTTP 服务；不宣称完成普通浏览器网络通道的端到端测试。新 CI 只运行 Studio 合同与 JS 语法测试。

本轮没有调用真实 Codex/Claude 服务；启动监督测试中的 Popen/authorization 是明确标注的模拟。读取进度使用当前 SQLite 合同的测试夹具，不冒充模型运行。新增独立 Claude 源码审核、用户实际任务试用和主线验收待完成。此版本先以开发分支/PR 交付，不自动合并 main。
