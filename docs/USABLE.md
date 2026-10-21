# DevFlower Stable Studio

Studio 的业务项目与私有数据目录分离。`tools/devflower_studio.py` 保留原有只读发现和固定任务入口；`tools/devflower_usable.py` 提供固定 Stable 下的工作区、工作流、任务授权与受控执行入口。

## 启动与信任

`devflower_usable.py` 只从**外部已审核的独立 Stable 副本**运行。它不提供把当前候选批准成 Stable 的 HTTP 或 CLI 接口。外部发布操作者需先冻结完整源码、合同和 Git tree，取得独立审核，再把固定副本及审批记录交给运行操作者。审批记录绑定完整文件清单、候选 SHA256、Git commit/tree、原始审核回执 SHA256 与批准引用；命令行额外固定审批文件自身 SHA256。文件哈希验证不能替代外部审核。

初次配置由本机操作者执行，不修改全局认证，也不复制整个原生 HOME：

```bash
python3 /path/to/Stable/tools/devflower_usable.py configure \
  --stable-approval /private/stable-approval.json \
  --stable-sha256 <外部审批文件SHA256> \
  --authority /private/new-authority \
  --workspace /private/new-studio-data \
  --native-homes /private/new-native-homes \
  --allow-root /path/to/Development \
  --repository owner/repository \
  --codex /path/to/codex \
  --codex-credential /original/home/.codex/auth.json \
  --codex-dependencies /path/to/node_modules/@openai \
  --codex-model <已批准模型> --codex-effort <已批准强度> \
  --claude /path/to/claude \
  --claude-credential /original/home/.claude/settings.json \
  --claude-model <已批准模型> --claude-effort <已批准强度> \
  --verification-profiles /private/verification-profiles.json \
  --gh /path/to/gh --gh-config /private/github-cli-config
```

若经实际诊断确认中转服务会丢失并行流式工具参数，可在初次配置加 `--claude-buffered-tools`。该选项绑定到操作者配置和任务授权：仅在单次 Claude 调用期间使用本地认证代理，向原 HTTPS 服务请求完整非流式响应，再将实际返回的文本/工具参数按标准 SSE 格式送给原生 CLI；保持模型、effort、工具权限及响应内容不变。流内增量文本会等到该次模型回复完整到达后显示。它不修改全局设置、不补造工具参数；未知模型/effort、认证缺失或请求重定向均拒绝。默认关闭，原生会话恢复仍要求同一受批准 profile。

三个私有目录必须是新目录，且与 Stable、Development、认证文件及 GitHub 凭据分离。此配置输出 operator 路径及其 SHA256。后续只需：

```bash
python3 /path/to/Stable/tools/devflower_usable.py serve \
  --operator /private/new-authority/operator.json \
  --operator-sha256 <配置SHA256> --port 8765
```

打开终端打印的私有 URL。访问能力仅位于 URL fragment 和浏览器会话存储中，不由 HTTP 返回、不进入访问日志或 Agent 环境。不要把该链接提交到源码或任务文档。服务重启使用相同配置及私有目录；浏览器关闭不会结束 worker。操作者可在自己的服务管理器中运行上述命令。

## 从工作区到运行

1. 在 Studio 输入本机 Git 仓库绝对路径并打开，或选择最近工作区。后端核验允许目录、真实仓库根、远端身份和保护路径。
2. 默认直接进入可编辑的空白工作流，无需选择 A/B/C。点击“新建空白工作流”立即开始；“模板库（可选）”可填充精简开发 A、规划开发 B 或研究确认 C。它们只决定初始节点，不是执行模式或权限入口。主视图始终为占满工作区域的画布，浮动工具栏管理工作区、流程、保存和设计/运行切换。从节点库拖入节点，或双击空白处选择节点。单击选择、双击打开浮动配置；输出端口拖到目标节点即可连接，拖到空白处可选择并自动接入下一步。节点旁的加号、连线上的插入/删除操作与右键复制/删除都修改真实草稿，可撤销/重做。Reviewer 的橙色端口用于修复回路。空白处拖动平移，滚轮或按钮缩放，适应画布显示全部节点；支持撤销/重做、Delete 删除及 Escape 取消未完成拖动。保存保留不可变 revision，并对并发修改做 CAS 校验。
3. 配置节点的 Provider、角色、职责、背景、工具、原生会话、模型、effort 和时间预算。模型和 effort 只能使用操作者实际批准的 profile；`unknown` 请求继承该 profile。无法从 CLI 响应证明的实际值仍显示 `unknown`。
4. 点击画布的 Human Gate 节点，填写任务卡或导入授权仓库的 GitHub Issue URL。任务、路径、验收与授权预览均在该节点的画布内面板操作；Delivery 节点配置当次交付权限。确认目标、允许修改路径、验收正文与测试节点。验证节点可选择操作者预先登记的 JSON 输入/输出断言、固定 DevFlower `baseline` 或 JavaScript 语法检查。浏览器只能选 profile，不能提交任意 shell 或定义命令。
5. 在 Human Gate 面板生成当次授权预览，核对工作区 HEAD、源码哈希、合同、Agent 配置、步骤预算和 GitHub 权限。每个人工关口均明确标注必填内容，客户端在发送前检查每条回复非空（最多 4000 字），为空时显示中文提示、聚焦缺项并保留可操作按钮；服务端继续校验全部人工合同。发送后遇到网络异常则可能已消费许可，按钮保持锁定，应查询运行记录，不盲目重发。授权只能使用一次；源代码、配置、Stable 身份变化后旧预览失效。
6. 点击人工确认并运行。固定 runtime 依次执行可选 Planner、Codex 实施、完整候选冻结、真实测试、Claude 独立审核、确定性 gate 和当次批准的交付。NEEDS_CORRECTION 自动进入新候选修复、重测和复审，最多 5 轮。基础设施安全重试最多 2 次；未知会话不能猜测重启。

v2 工作流的人工关口完全由节点决定：启动前至少一个授权节点；Reviewer 与 Delivery 之间可以放置一个或多个结果确认节点。任何模板或空白流程都适用同一规则，C 仅预填研究问题。结果节点存在时，审核通过后进入 `AWAITING_HUMAN`；用户须逐节点回答，确认请求绑定当前候选、合同及严格整数轮次，回执还绑定工作流哈希。未完成全部结果确认不能交付，恢复按钮也不能跳过。删改草稿不会修改已授权运行，新的执行必须重新确认。

v1 草稿被打开编辑时，只转换为内存中的 v2 副本并明确提示；保存通过原 revision/CAS 创建新版本，旧 revision 不变。旧运行、旧 C/G4 回执以及历史 SHA 均按 v1 规则读取，不能以改写版本号的方式复用原授权。新执行使用 v2；引擎仍保留 `policy.mode=B` 作为兼容序列化字段，但它不是用户可选择或限制编辑的模式。

当前执行器支持顺序流程和一个 Reviewer→Developer 修复回路。并行 DAG、任意循环、子 Agent、浏览器 shell、原生会话归档/删除不支持，相关配置会被拒绝。编辑画布不授予执行权限，也不能移除冻结、测试、独立审核和交付 gate。

## 原生会话与监控

M0 发现接口继续只读扫描原生会话；未托管会话显示“发现/运行未确认”。托管会话在专用持久 HOME 中保存原生记录，并显示 HOME、配置根、原生目录、项目、角色和确切 UUID。恢复要求同项目、同角色、明确 UUID；一个 HOME 同时只能有一个运行持有会话锁。

Codex 只读挂载原认证文件到独立 `.codex/auth.json`；Claude 只读挂载明确批准的 settings 文件。CLI 写入自己的原生会话目录，不覆盖全局认证或其他项目会话。恢复仍使用原 HOME 和同一只读认证绑定。

切换“运行快照”仍使用同一主画布，按所选 run 的固定工作流显示用户节点；切回“设计草稿”恢复独立的编辑内容。监控显示真实 run ID、worker/Agent PID 与启动身份、实际活性、轮次、测试计数、审核结论和缺陷、候选与合同哈希、代码差异及 GitHub 回执。点击 Verifier 查看其自身合同、实际计数和结果，Reviewer 查看实际裁决与未关闭缺陷，Developer/Reviewer 查看固定候选 diff 与原生会话，Delivery 查看 commit/push/PR 阶段与已读回链接。固定 Controller 的冻结、验证和交付 gate 在节点结果中另列，用户连线不能移除它们。切换运行或延迟响应不能覆盖其他运行。节点及连线仅显示当前证据，不使用动画暗示运行。面板可用 Escape 关闭，节点支持键盘聚焦并用 Enter/空格选择；拖动端口时收起配置面板以免遮住目标。没有活着的 worker 时，遗留执行阶段显示为需要恢复。网络错误显示状态未确认，不保留虚假的当前 ACCEPT。

恢复前检查实际进程、原源码、候选、合同及 Git 状态；未知副作用不自动重做。停止操作仅取消本任务持有的进程，已经成功的远端副作用不回滚。

## GitHub 交付

本 profile 的交付选择为“仅审核”，或同时授权 commit、正常 push 与开发 PR。目标仓库来自操作者配置；分支必须是开发分支，PR base 固定为 main。已有 PR 必须在本次预览中绑定。

提交使用独立 Git index 和完整候选 blob，核验实际 tree 与被审清单；内部持久 ref 保存本地提交，不覆盖原工作树中的用户文件。push 记录意图、检查预期远端 tip、执行正常快进并读回。请求超时先查询远端；PR 创建同样先查询并在回执丢失后读回。推送成功但 PR 创建失败会保留部分交付记录，不能冒称原子完成。

Agent 无法读取 GitHub 配置、授权或权威状态。Studio 不提供 merge、force-push、删分支、Tag 或 Release 接口。交付后可按回执中的提交和 PR 查看结果；原工作区分支不会被隐式 reset。

## 验证

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
python3 tools/devflower.py check --baseline
PYTHONDONTWRITEBYTECODE=1 python3 tests/host_isolation.py
node --check tools/studio/static/usable.js
PYTHONDONTWRITEBYTECODE=1 python3 tests/usable_browser.py \
  --chromium /path/to/chromium --node /path/to/node \
  --playwright-module /path/to/playwright --artifacts /outside/source/browser-evidence
```

验证器默认保留 Landlock；需要创建独立子进程的测试，可由本机操作者在初次配置时显式选择 `--verification-isolation bwrap`。此选择进入固定 operator 配置和当次授权预览，浏览器不能自行切换。bwrap 使用只读候选和 PID namespace；原始项目、授权及交付凭据不可见，超时或监督进程结束会终止 namespace 内的后代。

部分 Linux 安全策略禁止在 bwrap 内再次创建 user namespace。这种环境下，测试自身启动嵌套 bwrap 会实际失败，不会计为 Skip 或 PASS。DevFlower 的完整宿主隔离回归由固定外部监督在宿主执行；Studio 内选择该任务实际可执行的非零测试集合，两类证据分别记录，不互相替代。

原生模型 HOME 保持持久；每次进程只获得自己的短路径临时目录，进程结束后清理，不影响原生会话恢复。

`tests/test_usable.py` 与 Chromium 用例使用确定性 fixture 验证边界和竞态。它们不代表真实模型验收。完整任务验收还需要真实 Stable Studio 发起、实际人工授权、原生 Codex/Claude、非零测试、至少一次真实修复复审，以及经读回确认的开发 PR。各次执行的证据和最终独立裁决留在项目任务档案，原始大日志留本地。


完整验证请在固定源码的独立测试副本运行，避免在已固定 Stable 内生成缓存或产物；其完整 manifest 包括所有非 Git 文件，任何新增文件都会阻止启动。Studio 在授权预览前拒绝包含 ignored 产物的 Development 工作区，避免先消费授权再失败；请选择干净的独立开发 clone，不自动删除用户文件。

验证计数来自可信父进程：每个登记的 JSON 断言实际启动一个隔离子进程，传入固定输入，父进程将输出与授权绑定的预期值比较，并自行计为一项检查。子进程无法写权威结果目录；伪造 tests/failures、提前退出、缺少输出、重复 JSON 键或非有限数值均不能通过。baseline/JavaScript 只计为一项外部命令检查，不冒充 unittest 用例数量。断言的语义和覆盖范围仍必须经独立源码审核。

候选测试与 unittest 报告器共处一个 Python 进程时，测试代码能伪造计数或生命周期协议。因此本版不支持把这类自报计数作为执行门禁：旧 task/JUnit 仍可读取、展示和做离线格式校验，新的 run/resume 拒绝未经迁移的旧报告器。完整 Python 回归继续由固定外部监督运行并保存原始数量/失败/Skip，不能以 Studio 的有限行为断言替代。`init/new/index/check` 保持兼容；`examples/orchestrator/prepare.py` 已使用六个父进程断言。

操作者在首次部署时登记固定测试命令、输入、预期 JSON 与必要的外部只读文件；其依赖哈希进入 operator 和每次授权。业务用户在 UI 选择已有 profile，不需要编写 task/operator JSON。可从仓库提供的示例生成 DevFlower 行为断言注册表：

```bash
PYTHONDONTWRITEBYTECODE=1 python3 examples/usable/verification_profiles.py > /private/verification-profiles.json
```

该示例分别检查 A/B/C 模板的实际编译结果和空白图的拒绝结果；它只覆盖这四项行为，任务需要的其他断言应由操作者按验收合同增加。

历史 v1 Stable 的 C 运行仍必须使用结果产生后的 deferred G4；旧 CLI 的四个前置引用仅为兼容协议。新 v2 执行不读取 C 标签决定关口，改由工作流中的结果确认节点及其实际回答约束交付。

工作台以主画布为操作空间，不再用四个页面承载主要操作。Human Gate 按任务、范围与验收、确认运行三个步骤承载任务、Issue 导入与授权；修改任务或工作流后旧预览立即失效。Agent 节点承载模型、effort、明确原生会话、预算和工具；Verifier 承载合同与结果；Delivery 承载交付权限和真实回执。工作区与流程控制使用紧凑浮动工具栏，节点库可收起，配置和执行证据是画布内浮层。画布和连线只是草稿；“校验执行顺序”检查当前版本，修改后旧校验失效。运行配置、模型与会话绑定在授权预览中再次检查。慢于轮询间隔的快照不会被持续丢弃，切换运行仍只接受当前选择的响应。刷新页面可恢复已选工作区及可见的原运行，但不会自动消费授权或重启 Agent。


## 用户工作流身份合同

`Runtime.prepare` 在已签名执行 config 中保存可选的 `studio_workflow`，闭合字段仅为：

```json
{"document": "完整工作流快照（对象）", "sha256": "compile_plan(document).sha256", "verification_ids": {"用户Verifier节点id": ["实际生成的验证合同id"]}}
```

`config_check` 重新编译完整顺序图，核对 hash、映射覆盖、唯一性、节点归属、合同顺序及 `policy.verification`；兼容 policy 字段、轮数、角色及实际结果确认节点也必须一致。命令、运行绑定和权限仍由 operator 与执行 policy 控制，这个字段不提供执行能力。旧记录无此字段时保持兼容并显示原执行图。

`snapshot.workflow_graph` 按编译顺序返回 `nodes`，保留用户 id/type/label/位置、原始 `edges` 和 `sha256`，另带 `run_id`、`round` 与证据驱动的 `edge_states`。节点状态限定为 `passed/failed/pending/running/blocked`。投影只白名单输出安全显示数据，禁止返回节点 config、职责/背景、认证、完整任务正文或任意命令。

每个 Verifier 仅聚合映射中的本轮合同，证据同时绑定 run、round、当前候选和验收 hash；旧轮、其他候选或其他合同不能提供当前 PASS。实际进程退出只代表执行结束，必须由 Controller 验证结果后才可 passed。当前 Agent 活性还需匹配当前阶段、当前轮的进程身份与活 worker；历史裁决、未确认进程和网络故障不能显示为当前 ACCEPT/RUNNING。Planner 的已完成计划属于本 run，其余实施、验证、审核与 G4 均有本轮边界。

`VALIDATED` operation、最终验证报告和审核报告的 round 都须精确等于当前轮次；不能用“历史轮次不大于当前轮次”代替。round 缺失、为空或不匹配时，按未绑定证据处理，不补填当前轮次，不据此显示 PASS/ACCEPT，也不应导致整个快照读取失败。自验和独立复审只证明各自实际检查的完整候选，源码改变后须重新验证，旧验收不能批准新候选。

Verifier 的计数必须恰含 tests/failures/errors/skipped 四个非负整数，tests 非零且失败、错误、Skip 均为零，才能显示 passed。Studio 的父进程断言每项实际计 1 用例、零 Skip，不提供候选自行上报计数或扩展验证配置的入口。已绑定当前身份的 `VALIDATED` operation 表示 Controller 已验证，最终报告尚未落盘也可据此显示结果；不能为它伪造进程回执。没有匹配 operation 时，最终报告还须自带实际进程回执：exit 为 0 且 timeout/overflow/cancelled 均明确无异常。回执缺失、字段不全、退出失败、超时、输出溢出或取消，即使报告声称 passed 且计数全绿，最终报告回退也显示 failed；连报告都没有时保持 pending。

审核节点保留所有 findings 的安全显示字段及全部未 CLOSED 的 open_findings 计数，阻断判断另按机械 gate 的必需缺陷定义：P0/P1，或关联 `required_contracts` 的 P2。P3 与未关联必需合同的 P2 建议可以保持 OPEN，不使当前 ACCEPT 误显 blocked；必需缺陷未关闭仍阻断。只有当前身份绑定的 ACCEPT 可显示 passed，ACCEPT_WITH_LIMITATIONS 仍为 blocked，NEEDS_CORRECTION 为 failed。投影仅显示证据，不能授权交付或代替 Controller gate。

合同与 Python/Store/HTTP 反例：`python3 -m unittest discover -s tests -p test_studio_workflow.py -v`，覆盖真实 Python 父进程报告、矛盾 PASS、缺失/失败/超时/溢出/取消回执、非法计数与可选/必需意见。`tests/usable_browser.py` 继续保留原竞态，并覆盖画布任务导入、空确认发送前阻止/改正、发送异常锁定、配置保存、同画布快照隔离、各节点结果入口、旧轮/失败/死 worker 负例。它们使用显式 SQLite/HTTP 夹具，不能当成真实模型、真实 Stable 任务或独立人工可用性证据；固定外部断言、候选绑定的完整回归和独立 Claude 审核须另行记录，小范围修复自验不代表整个 Issue #6 完成。长私有路径下 Chromium socket 可用 `BROWSER_TMPDIR` 指向操作者自己持有的短目录别名，产物仍留在指定的本地证据目录。

本轮允许 Codex 代理填写并点击指定任务的 GUI 启动，仅代表用户授权下的代操作。若实际执行，原始回执及验收证据须分别记录授权来源为用户、实际操作者为 Codex；不能把它称为用户亲自点击、独立人工可用性验证，也不能推广到其他任务。候选不能自行更新 Stable pin 或制造此类审批记录。

## 模板解耦与持续回归

新增 `tests/test_template_governance.py` 覆盖模板来源不影响执行、任意数量的起始/结果确认、逐节点回答、过期候选/轮次/图回执拒绝、旧版只读兼容和迁移后重新授权。`tests/template_browser.py` 使用真实本地 HTTP/Chromium 验证空白入口、可选模板、删除 C 默认关口、A 添加结果节点和旧草稿版本保留。此套件不使用真实模型。

`.github/workflows/usable.yml` 对 tools/tests 等变更执行完整 Python 回归、baseline、四个前端语法检查、实际宿主隔离，以及五组普通 Chromium 测试。隔离能力缺失计为失败，不通过 Skip 假装验证。GitHub Actions 只运行合成任务，无模型调用、用户凭据或生产仓库；归档仅含已提交公开源码身份、测试日志和合成截图，不上传本机原始会话。

该代码仍须作为新候选独立审核并固定发布，不能覆盖正在运行的 Stable 目录。历史 Stable 审批不自动批准本次修改。
