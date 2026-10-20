# M2-R0 方案收敛与五项设计决定

Codex第一套方案在Claude独立稿形成前已写入并本地保存；双方有共同结论，并非Codex事先采纳Claude结论。两份初稿、第一轮报告均原样保留。最新规范以architecture.md/acceptance.md为准。

## 双方案差异与取舍

| 议题 | 独立观点差异 | 选择及理由 |
|---|---|---|
| 存储/发布 | Claude偏好catalog.sqlite3 + 每索引schema3事实DB；Codex偏好当前多index单库模式，新增schema4元数据 | **一个schema4数据库**内保存完整索引、workspace/attempt/catalog性质的表及默认指针，同一SQLite事务发布。不是独立catalog文件，不另建current文本指针或每索引meta文件。当前index.py:339–361已能事务插入完整多索引事实；新增range/identity字段又确需protocol3/schema4。独立catalog会额外引入事实文件、meta和catalog之间崩溃恢复协调，首阶段收益不足。保留旧schema3原库作为兼容/回退；显式新路径导入旧事实，legacy不假装可作新Diff。 |
| 捕获中/封存后改动 | Claude建议pre/post发现host任何变化均失败；Codex区分捕获变化与封存后host变化 | 捕获时检测到变化重试一次/失败；封存后仅分析sealed向量，host再编辑只提示workspace_changed_since_capture，不混读、不把该向量冒充最新磁盘。不能证明任意多文件同一瞬间，明确记录manifest身份。 |
| HEAD标签 | Claude独立稿建议dirty时git_commit_id为空；Codex初稿强调HEAD仅provenance但字段易混淆 | 采用显式base_git_head与represented_git_commit：后者仅raw Git-tree或严格向量相等时有值。ignored配置变化也不能仅凭git clean冒充HEAD。 |
| 依赖证据 | 双方认为positive file read-set不完整，Claude原稿仍留negative lookup获取未决项 | 不等待完整failed-probe扫描器：namespace新增/删除/重命名/类型/搜索根改变统一全量失效，内容修改按完整read-set失效；LLVM18 callbacks仅解释/补充。该保守方案覆盖可选头新增和遮蔽反例，不宣称精确最小失效。 |
| Diff | 双方要求位置与语义分离；Claude独立稿一处call key仍含instance_id，并把位置无关配对留为heuristic | semantic relation多重集完全独立于位置ID；site配对只在同caller、AST/token/macro证据满足严格唯一双射时确认。重复/插删/不完整范围明确ambiguous/unmatched，不依近似行号/ordinal猜测。ODRHash仅提示，literal定义修改靠实际字节范围。 |
| 成本 | 双方均避免delta facts；Codex初稿toolchain/symlink规则仍需细化 | 小的完整输入bundle + 最小运行文件视图，不复制整个/usr。普通标准头必须通过；项目链接明确限制，受信工具链alias必须验证封存命名空间；B先full shadow验证，不把cache-only测量称为端到端加速。 |

第一轮comparison将Codex描述成“独立catalog”及“修改后不发布”，与初稿的单SQLite元数据表、封存后host变化合同不一致。此处明示差异，未改写独立原文；第二轮须重新审核当前完整规范。

## 五项实施前决定：规范已固定，生产实现尚未发生

1. **捕获与权限**：descriptor安全复制成sealed向量；输入内容/命名空间/编译可观察属性hash，root映射不重叠，project/dependency链接明确拒绝，toolchain alias仅在封存授权空间内验证；最小ELF运行文件与frozen include/resource树，无live /usr回退。普通FS不承诺跨文件瞬时原子。M2-A必须实现并通过捕获并发、越根/alias/标准头正负例；R0两个owned挂载探针仅证明本机路径/头文件视图可行，不是生产capture安全证据。
2. **LLVM18与负向依赖**：实际SourceManager buffers + opt-in system dependencies/PPCallbacks；读不到完整negative probes并不放松。任何include namespace结构变化全量失效；B只在结构稳定且read-set/命令/工具链/元数据完整一致时复用。volatile builtin记录真实上下文且不复用。复杂PCH/modules不支持，不能默默复用。
3. **Git HEAD/profile**：raw ls-tree/cat-file，无checkout/filters/hooks/build。base_git_head仅来源记录，dirty时represented_git_commit为空；HEAD缺生成文件/历史ccdb时明确阻塞该比较侧。可显式配置带来源的共同外部输入，不擅自混入Workspace生成结果；Git对象/alternates授权、fsmonitor与可选索引锁禁用均须验收。
4. **发布/迁移/生命周期**：单schema4 SQLite，完整事实与CAS默认指针一次短事务，失败attempt另存；FULL同步、局部文件系统fsync/no-overwrite新库发布。旧source快照BLOB在索引中，不依赖可丢弃TU缓存或某个live目录；captured未被实际解析的文件不自动开放source全文。新路径显式legacy导入，禁止query迁移。A不自动GC；B仅显式dry-run/确认prune且保护latest/pins/leases，停用reuse回退A。
5. **protocol3与配对**：保留semantic USR/链接owner/logical TU，定义Clang范围+buffer hash，index-local instance保持；relation key不含位置或旧instance_id。architecture §11.1的同caller规范化token/AST/macro唯一候选双射是确认site target_changed的必要条件；unique simple替换必须通过，重复候选必须保留不确定。没有有效定义范围时返回unavailable，不能用ODRHash冒充语义证明。

上表决定使M2-A可按A1–A6任务包实施，M2-B按B1–B3另行验收。它们是要实施的明确合同，不是把M2功能或所有边界标为已验证。
