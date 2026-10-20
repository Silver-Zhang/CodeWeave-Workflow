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
2. 从 A/B/C 起始模板或空白创建流程。左侧添加节点，中间拖动布局，右侧编辑配置；从输出端口拖到目标节点即可连接，Reviewer 的橙色端口用于修复回路。空白处拖动平移，滚轮或按钮缩放，适应画布显示全部节点；支持撤销/重做、Delete 删除及 Escape 取消未完成拖动。保存保留不可变 revision，并对并发修改做 CAS 校验。
3. 配置节点的 Provider、角色、职责、背景、工具、原生会话、模型、effort 和时间预算。模型和 effort 只能使用操作者实际批准的 profile；`unknown` 请求继承该 profile。无法从 CLI 响应证明的实际值仍显示 `unknown`。
4. 粘贴任务卡，或导入授权仓库的 GitHub Issue URL。确认目标、允许修改路径、验收正文与测试节点。验证节点可选择操作者预先登记的 JSON 输入/输出断言、固定 DevFlower `baseline` 或 JavaScript 语法检查。浏览器只能选 profile，不能提交任意 shell 或定义命令。
5. 生成当次授权预览，核对工作区 HEAD、源码哈希、合同、Agent 配置、步骤预算和 GitHub 权限。每个人工关口必须有真实用户回复。授权只能使用一次；源代码、配置、Stable 身份变化后旧预览失效。
6. 点击人工确认并运行。固定 runtime 依次执行可选 Planner、Codex 实施、完整候选冻结、真实测试、Claude 独立审核、确定性 gate 和当次批准的交付。NEEDS_CORRECTION 自动进入新候选修复、重测和复审，最多 5 轮。基础设施安全重试最多 2 次；未知会话不能猜测重启。

C 模板在开始前记录实际 G1–G3 回复，审核通过后进入 `AWAITING_HUMAN`。用户看到实际候选、测试和审核结果，再完成 G4 结果解释；该回复绑定这一轮候选和合同。未完成 G4 时不能交付，也不能由“恢复”按钮跳过。

当前执行器支持顺序流程和一个 Reviewer→Developer 修复回路。并行 DAG、任意循环、子 Agent、浏览器 shell、原生会话归档/删除不支持，相关配置会被拒绝。编辑画布不授予执行权限，也不能移除冻结、测试、独立审核和交付 gate。

## 原生会话与监控

M0 发现接口继续只读扫描原生会话；未托管会话显示“发现/运行未确认”。托管会话在专用持久 HOME 中保存原生记录，并显示 HOME、配置根、原生目录、项目、角色和确切 UUID。恢复要求同项目、同角色、明确 UUID；一个 HOME 同时只能有一个运行持有会话锁。

Codex 只读挂载原认证文件到独立 `.codex/auth.json`；Claude 只读挂载明确批准的 settings 文件。CLI 写入自己的原生会话目录，不覆盖全局认证或其他项目会话。恢复仍使用原 HOME 和同一只读认证绑定。

监控显示真实 run ID、worker/Agent PID 与启动身份、实际活性、轮次、测试计数、审核结论和缺陷、候选与合同哈希、代码差异及 GitHub 回执。页面切换或延迟响应不能覆盖其他运行。没有活着的 worker 时，遗留执行阶段显示为需要恢复。网络错误显示状态未确认，不保留虚假的当前 ACCEPT。

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

Stable 自举的 C 模式必须使用结果产生后的 deferred G4；旧 CLI 的四个前置引用仅为原有兼容协议，不满足 Stable 自举的结果解释关口。

工作台将工作流、任务与授权、进度结果和原生会话分为四页。画布和连线只是草稿；“校验执行顺序”检查当前版本，修改后旧校验失效。运行配置、模型与会话绑定在授权预览中再次检查。慢于轮询间隔的快照不会被持续丢弃，切换运行仍只接受当前选择的响应。刷新页面可恢复已选工作区及可见的原运行，但不会自动消费授权或重启 Agent。
