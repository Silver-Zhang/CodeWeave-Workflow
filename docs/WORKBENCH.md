# Development Agent 工作台

这是独立的 Development 预览，不能签发 Stable 批准。旧 Studio、v1/v2 草稿、授权和历史仍由原入口读取；v3 工作流另存，不迁移正在执行的旧任务。

## 日常操作

1. 从部署者提供的“打开工作台”入口进入。顶部显示 Development、当前源码版本和 Linux Runtime；私有登录地址不要公开分享。
2. 点击“打开文件夹”，在标明运行器机器的窗口选择目录。可返回父目录、选择已批准位置或最近目录，也可以取消。打开目录只读取信息，执行和写入需要当次授权。
3. 选择三个示例之一，或添加 Agent、条件、汇合、循环、确认和结果节点。拖动节点调整布局，从右侧连接点拖到下游左侧连接点。点击节点打开就近配置，空间不足时固定侧栏。
4. 基本页分别设置名称、职责、工具、会话、模型、强度和 Ask/Plan/Agent；提示词页设置初始化、每轮任务、输出要求；高级页限制权限、上下文、超时和预算。模型目录发现、认证配置、实际推理成功是不同证据。
5. 填写任务，保存后点击“开始运行”，核对目标、权限及预算，再确认。运行自动打开冻结画布；修改下一次流程需点击“编辑草稿”。历史运行可在画布工具栏切换。
6. 在节点上看真实状态、轮次、等待对象和结果；点连线查看实际交接。底部可展开事件和实际发送内容。暂停只停止新节点调度，当前进程继续；停止取消本任务拥有的进程。网络中断显示“状态未确认”，请查询恢复，勿重复启动。
7. 左侧搜索并打开同一原生会话。默认聊天显示可见消息，完整请求、工具活动折叠；不展示隐藏推理。会话管理明确区分 DevFlower 别名/分类、原生改名/归档、可恢复回收站；没有自动过期或永久删除。原生终端页提供受保护的本机打开命令，不在浏览器中自动启动第二个会话写入者。

## 可执行语义与边界

- 顺序图、显式 fan-in 汇合、类型化条件和最多五轮的循环由确定性调度器执行。无界环和隐式多路 Agent 输入被拒绝；未选择分支显示跳过。汇合按运行、节点路径及完整祖先轮次关联输入。
- 每个 run+节点路径只拥有一个原生会话；首轮合并发送一次本次初始化，之后循环不重复。新运行即使恢复同一 UUID 也追加本次初始化，保留原历史。模型输出不是运行状态、独立审核或交付批准。
- 两个只读 Agent 可以并发；可写节点与同一源码的其他节点互斥。Ask/Plan 使用外层只读挂载，Agent 只能修改授权工作区；Git 元数据另行只读。提示词保护不能替代这些强制边界。
- 传递最终回答、结构化字段或附件引用，不默认复制聊天历史。交接保留来源，超过预算明确截断，接收方重新核验附件访问权和内容哈希。上游建议不能增加权限。
- 原生恢复要求原 HOME、cwd、真实 UUID、模型/强度、记录身份与空闲状态均可核验。导入、多 cwd 或原环境不明的记录只查看或明确复制可见上下文新建。原生分叉创建新 UUID，保留父记录；独立审核不得复用开发会话。
- 状态与事件存储在 SQLite 事务中。重复启动必须匹配同一授权；恢复先检查真实进程、源码、原生记录和独立完成回执。结果不明的回合及原生元数据操作停止等待核验，禁止盲目重发。
- 验证/交付节点只接受部署者固定配置的外部执行器，浏览器不能提交命令。没有配置时显示具体缺项；没有真实审核、有效测试及远端读回不得声称交付。该 Development Controller 的研发由外部固定监督审核，不允许自批自身。
- `tools/devflower_stable_bridge.py` 是连接已授权 Stable 运行的部署适配器：验证节点核验 Stable 实际测试的完整套件、非零计数、进程与原始回执；交付节点重新执行 Stable 的完整门禁并正常推送、读回。中断后查询远端，不盲目重复推送；两库部分成功如实保留。它不会创建授权、批准 Stable 或把画布中 Agent 的 ACCEPT 当独立审核。
- Copilot 未通过本机认证、隔离执行及实际推理验证前不可选。原生 ACP 能力探测或空会话建立不等于模型验收。Provider 不可用会失败并跳过依赖节点，不伪造回答或换模型。

## 部署与开发

前端静态资源随仓库提供；普通启动不需要 Node/npm。部署者需 Python 3.11+、Git、Linux bwrap、显式隔离的原生工具及只读认证挂载。服务只监听 127.0.0.1，按端口隔离浏览器能力，不使用跨 localhost 端口的认证 Cookie；禁止将它直接暴露到公网。

高级部署入口是 `tools/devflower_workbench.py`，明确传入 operator、policy 及完整候选哈希。策略中的模型来自原生发现或有来源标注的显式登记；模型和 effort 沿用用户批准配置。源码变化需生成新的 Development 快照与配置 pin，不能覆盖运行中的 Stable。

部署 Stable 桥接时，将适配器副本和私有配置放在 Development 之外。配置固定现用 Stable 的批准记录及哈希与私有授权目录。固定外部监督在实际启动后写入每个 run 的独立授权，绑定控制目录、已有 Stable run，以及工作台的 run/source/candidate/graph/authorization 身份。外部 payload、逐 run 授权的 `binding` 与回执均必须包含 `acceptance_sha256`：对本次冻结任务卡的原始 UTF-8 字节计算 SHA256，保留换行及首尾空格，并与原 Stable run 的 `acceptance_sha256` 完全相同；旧授权缺此字段或任一身份不匹配均拒绝。桥接仅等待并读取，不创建授权。GitHub 客户端配置只由外部执行器读取。使用 `python -I -B <固定副本> --config <私有配置> --config-sha256 <哈希> --kind verify`（或 `delivery`），在策略中固定解释器、脚本、配置及全部导入目录的哈希和最小挂载范围，私有运行数据作为单独挂载。没有外部授权绑定的研发运行不能通过此桥接交付；本轮 DevFlower 自身交付仍由固定外部监督重新检查，不由新 Controller 自批。

前端重建：进入 `tools/studio/workbench_ui`，执行 `npm ci` 和 `npm run build`；也可将 `DEVFLOWER_UI_DEPS` 指向外部依赖缓存再执行 `build.mjs`，避免把 node_modules 放入源码候选。精确版本见 package-lock.json，许可证见同目录 THIRD_PARTY_LICENSES.txt。

新增协议回归由 `test_workbench*.py` 运行；普通 Chromium/真实 HTTP 回归入口为 `tests/workbench_browser.py`。它使用明确标注的合成原生数据，不能替代真实 Provider、完整源码审核或用户最终验收。

## 参考实现与来源

- [VS Code Agent sessions](https://code.visualstudio.com/docs/agents/run/sessions/manage-sessions)：项目和命名会话布局。
- [Reap](https://github.com/vyagh/reap/tree/ad530a719d9bce927a9e3726c2c3f32fc77db523)，MIT，阅读 `internal/chat/restore.go`、`internal/cli/trash.go` 和 `internal/claude/live_unix.go`，参考恢复与占用检查。没有复制其代码，不调用自动清理、TTL 或 purge。
- [Codex App Server](https://developers.openai.com/codex/app-server/) 与本机导出的实际 JSON schema：模型目录和原生元数据调用。CLI 参数同时按安装版 help 核验。
- [Claude CLI](https://code.claude.com/docs/en/cli-reference)、[Copilot CLI](https://docs.github.com/en/copilot/concepts/copilot-surfaces/copilot-cli)：显式会话、能力探测与安全降级。
- [React Flow](https://reactflow.dev/)、[箭头](https://reactflow.dev/examples/edges/markers)、[边动画](https://reactflow.dev/examples/edges/animating-edges)：直接使用组件及其 Handle/ReactFlow 实现；状态由持久后端事件驱动，支持减少动态效果。
