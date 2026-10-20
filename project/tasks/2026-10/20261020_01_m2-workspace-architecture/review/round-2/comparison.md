# M2-R0 Round-2 双方案对比

## 身份

本轮 manifest raw SHA-256：`3e546ddd151ba17df2500ed930e0e2149f1ea314680651efc7124b7d075deb1b`；5个候选文件、62个冻结 M1 源文件逐项核验通过。source HEAD 为 `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`。本轮只审设计，未改源码。

## v1差异纠正

第1轮 comparison 的两处描述已在本轮按实际 v2 规范纠正：Codex方案选择的是**同一个 schema4 SQLite 内的 workspace/attempt/catalog 元数据表**，不是独立 `catalog.sqlite3`；封存后 host 修改时，分析仍可发布 sealed vector 并标记 `workspace_changed_since_capture`，不混读也不冒充最新磁盘，不是“一律不发布”。

## 审核结论

Codex v2 已实质解决第1轮五个实施前门槛，并比独立稿更具体：

- **捕获/权限/toolchain：** `architecture.md:47-56` 固定 descriptor-safe sealed vector、root不重叠、项目/依赖 symlink 拒绝、标准 toolchain alias 逐链验证、最小 runtime ELF 与 frozen resource/header tree、无 live `/usr` fallback；普通 `<vector>/<cstddef>` positive 和越界 absolute include negative 已列入 acceptance `16`。这是可实施边界，不再依赖未定义的全 `/usr` 快照。
- **negative include：** `architecture.md:100-115` 明确 PPCallbacks 不能证明每个失败探测，采用所有授权 include namespace 的结构变更全量失效；新增 optional header/shadow header/`__has_include` 反例在 acceptance `17`。没有错误承诺精确最小失效。
- **Git/profile：** `base_git_head` 与 `represented_git_commit` 分离；dirty/ignored compiler input 不冒充 HEAD；raw Git tree 使用 `ls-tree/cat-file`；profile含命令、root映射、toolchain/runtime及编译可观察 metadata。acceptance `09`、`38`覆盖。
- **发布/schema/lifecycle：** `architecture.md:76-94` 固定单 schema4 SQLite、短事务原子 default/CAS、失败 attempt、offline 新路径 schema3 migration、原库与旧 readers 保留、明确 prune/lease。与独立方案的独立 catalog不同，但单库选择可接受，只需实现 SQLite durability/crash tests。
- **protocol3/site pair：** `architecture.md:195-212` 固定 AST/token path、callee placeholder、macro structure、一对一唯一候选；重复调用输出 ambiguous，禁止 ordinal/行号猜测；acceptance `02/03/14`具备 adversarial oracle。

## 剩余风险与判断

没有当前必须返工的设计阻塞。以下是未来实现必须验证的常规高风险，不是当前 NEEDS_CORRECTION：

1. **Toolchain alias feasibility：** analyzer runtime ELF、Clang resource tree、`/usr/include`/标准头的最小视图需在目标主机实际收集；若 alias 链超出封存空间，必须返回 capture unsupported，不能退回 live bind。
2. **Filesystem capture：** pre/post/hash/descriptor 不能证明非合作写入的全局瞬时快照；方案已诚实采用 sealed vector身份，acceptance `10`必须验证中途修改和sealed tamper。
3. **SQLite crash durability：** 单库事务和新路径迁移必须在模拟 kill/ENOSPC/重启后核验旧 default 与完整事实。
4. **Call correspondence：** 语法 token算法必须实际实现 unique replacement 与重复 ambiguous 两个方向；算法失败必须保留 relation delta/unknown，而不升级为 target_changed。

Codex v2 的主要成本（schema4、protocol3、sealed capture、catalog表、A1-A6和B1-B3）由正确性/安全合同支撑；没有不必要的 delta facts、watcher、generic repository framework或M2-B提前实现。M2-A实施门已明确，但“implementation_ready”仅指设计门通过，不指生产代码已可验收。
