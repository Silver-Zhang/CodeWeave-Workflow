# Linux 本地运行器（v0.2-A 候选）

实现位于 `tools/orchestration/`，入口为 `python3 tools/devflower.py`。
原 `init/new/index/check` 不变。运行器不证明代码绝对正确；模型输出和
退出 0 均不能替代验证、授权或独立审核。本文件描述实现接口，完成程度
以独立 `project/devflower` 的当次证据为准。

## 命令

```sh
python3 tools/devflower.py doctor
python3 tools/devflower.py run --control /absolute/control --config /absolute/task.json --authorization /absolute/operator.json
python3 tools/devflower.py status --control /absolute/control --run RUN_ID
python3 tools/devflower.py audit --control /absolute/control --run RUN_ID --after 0 --limit 50
python3 tools/devflower.py cancel --control /absolute/control --run RUN_ID
python3 tools/devflower.py resume --control /absolute/control --run RUN_ID
python3 tools/devflower.py deliver --control /absolute/control --run RUN_ID
```

`run` 默认停在 READY；BLOCKED 的命令退出 1。`status/audit` 只读数据库，
不启动 Agent；事件分页最多 200 条。`cancel` 写取消请求，由监督者终止
本任务的进程组；状态记录实际停止结果。原始 stdout/stderr 同时有界读取，
仅保留字节数及哈希；不落盘隐藏推理或会话全文。结构化最终报告保留原字节哈希，并遮蔽已知模型认证值；候选含已知认证值时拒绝记录/交付。CLI 自身的本地 session 存储仅用于明确 UUID 恢复，不采集为 Controller 日志或提交入库。

## 操作员绑定

任务 JSON 的固定字段：

| 字段 | 含义 |
|---|---|
| task_id / project | 非空任务和项目身份 |
| source | 干净、独立 Git clone 的绝对路径 |
| acceptance | 操作员批准的验收合同文件绝对路径 |
| goal | 实施目标；作为数据传给实施者 |
| scope | 允许修改的相对文件或目录前缀 |
| excludes | 批准的候选排除目录/文件前缀，默认空数组 |
| policy | 设计目录 workflow-policy schema 的完整对象 |
| bindings | implementer / reviewer 的本地绑定 |
| prior_reviews | 可选；操作员绑定的原始历史审核，保留必需缺陷关闭义务 |
| delivery_targets | 可选；source 后可选 records，最多两个 |

每个 binding 有 `project, role, executable, home, read_paths, model, effort,
session_id`；可选 `isolation`（landlock/bwrap）与 `external_sandbox`（默认 false）。角色分别为 implementer/reviewer。`executable/home` 是绝对路径，
home 必须是角色专用运行目录，不能包含控制区、原仓库 Git 元数据或另一个
角色目录，也不能与原源码树重叠。`read_paths` 仅授予 CLI 程序及明确运行依赖的读取权限，不能是
`/`、`/home`、`/tmp` 等包含受保护目录的祖先。模型、强度沿用已批准的
本地配置，不提供默认型号；未知填 `unknown`。真实响应的 model/effort
没有字段就仍为 unknown，不能用请求值代填。

操作员在专用 home 中配置现有认证和模型路由。包括中转站时必须保留
该中转站的认证和映射；不要仅复制 OAuth 文件就假定可用。不得复制
业务 Git 凭据、SSH socket、其他项目会话、hooks 或插件。认证文件不入库，
不在命令行或日志中打印。环境默认过滤认证、Git、SSH 和 loader 变量；
仅保留无 userinfo 的既有 proxy 配置。测试进程从不获得模型认证目录。

授权 JSON 必需字段为 `config_sha256, acceptance_sha256, controller_sha256,
source, head, branch, approval_ref, external_source_approved, commit, push`。
哈希分别为任务 JSON 的 canonical JSON SHA256、合同原字节 SHA256、以及
`orchestration.common.controller_hash()` 的固定代码清单哈希。
`approval_ref` 指向实际用户授权；`external_source_approved` 是本任务向外部
模型发送源码的独立授权。项目配置不能自行签发授权，操作员必须独立审查。
此文件处于 Agent 无权访问的控制边界外，运行时捕获其原字节哈希。

验证 argv 必须用 `{result}` 绑定本轮唯一机器结果路径；`{artifacts}` 可用于
其他输出。结果格式是 JUnit 或 controller-json，后者恰有非负整数
`tests/failures/errors/skipped`。min_cases 至少 1；必需条款不可 Skip。
命令在冻结候选内执行，只有隔离 artifacts 可写。机器结果是证据之一，
审核仍需检查测试和实现是否被削弱。模型给出的路径及命令不会自动执行。

审核报告使用既有 review-result schema。必需合同必须有 PASS 和已知证据
引用（验证 id 或 source-inspection）；历史必需缺陷必须显式 CLOSED。
ACCEPT_WITH_LIMITATIONS 本期不允许自动交付。独立审核不能取得动态权限时
返回 BLOCKED，由外部受控 runner 补充命令证据再判断，不标为 Claude 亲自执行。

## 隔离与恢复

测试 runner 需要 Linux Landlock ABI >= 6；真实 CLI 可绑定 Bubblewrap。
能力须在实际宿主机检查：Codex 工具沙箱内不允许 namespace 不代表宿主机不可用。
不支持选定 backend 时阻断，不降级为可自动交付的提示保护。
每轮在真实子进程探测控制文件读写均拒绝。实施者只写源码副本及专用 home；
审核者只读固定候选，测试只写 artifacts。原仓库 `.git` 不进入副本。
控制进程关闭 dumpability；Landlock 限制跨域信号/abstract socket；其 seccomp
拒绝改变进程组/会话及跨进程内存接口。Bubblewrap 使用独立 PID namespace、
空根目录、只读运行依赖、明确 source/artifacts/home 挂载及只读根；超时终止
namespace 内的所有进程，包含 setsid 后的子进程。网络 egress 不隔离，因此外发源码
必须事先单独批准。系统 runtime 读取路径见 sandbox.py，不宣称通用容器安全。

本机 Codex 原生 sandbox 在外层隔离中不能再创建嵌套 namespace。仅当任务显式
绑定 `isolation=bwrap, external_sandbox=true` 且对应实际隔离探针通过，才使用
CLI 的 `sandbox_mode="danger-full-access"`，把执行边界交给外层内核沙箱。
这不是允许子进程越过 Bubblewrap：控制区、原仓库 Git 和交付凭据未挂载，
仅源码副本及专用 home 可写。该配置进入授权哈希；无 bwrap 时明确拒绝，
不以裸进程代替。默认仍是 workspace-write。模型和 effort 不随此配置改变。

SQLite 事务同时记录状态和事件，外部操作先写 intent。kernel flock 控制
run、原仓库及专用会话 home 的互斥；进程身份包含 host/boot/PID/starttime。
恢复先检查版本/授权/源树/实际进程，无法确认的阶段 BLOCKED。首次复制中断会保留残片并从已批准 Git 树重建；后续中断的
明确 resume 会从下一轮重新验证，绝不复用失去来源的 ACCEPT。最多 5 轮；
相同候选及阻塞集合连续两轮无新增证据停止。不能确定真实 session 的
进程失败不盲目重启，基础设施重试是上限而不是强制重复请求。

## 交付边界

产品的交付 backend 本期只接受显式绑定的本地 bare remote；真实业务远端
仍需独立授权和后续适配验证。框架自身的本轮真实 Git 交付由外部旧方式
完成，新 Controller 不为自身代码批准推送。

每个 target 固定 `kind, root, branch, remote, expected_tip`；records 另有
`receipt_path`（project/ 下 JSON）。原仓库必须保持干净，分支/远端一致。启动时完整文件清单必须等于已批准 Git commit，排除项不得漏掉已跟踪文件；不导入忽略的本地私有文件。
source 必须是 flow/work/feature/fix 功能分支，records 必须 project 分支。
不支持 active hooks、clean filters、submodule/LFS，发现即阻断；不绕过。

独立 index、原字节 blobs 和 commit-tree 构造被审 tree。提交意图固定 parent、
tree、作者、时间和 operation id；中断后得到同一 commit。不会改变用户
index、工作树或本地 ref；提交 SHA 由收据标识。正常 push 后读取远端；
回执丢失先读回，竞争则阻断，不 force/merge/rebase。source 成功后才在 records 原 Git 树上只新增/更新指定 JSON 收据，不复制忽略文件；
第二库失败标 PARTIAL_DELIVERY，不回滚第一库。构造出的源码 Git tree 重新按 blob 原字节计算清单，必须等于被审候选，防止构树间隙改变源码。

## 验证

```sh
python3 -m unittest discover -s tests -v
python3 tools/devflower.py check --baseline
python3 tests/host_isolation.py
```

模拟 CLI 是故障夹具，不是实际 Codex/Claude 验收。真实模型 fixture、
自举独立审核和本地 Git 故障测试分别记录版本、进程、候选与合同哈希。
