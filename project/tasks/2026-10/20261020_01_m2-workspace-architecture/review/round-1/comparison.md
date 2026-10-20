# M2-R0 双方案对比（独立审核第1轮）

## 身份与依据

Codex 候选 manifest raw SHA-256：`cc262acf82254468f3ff3e2652fdb974e419a0db822a28ae23ee6f489deb0a59`；设计文件3个、冻结 M1 源码62个。逐文件 bytes/SHA/mode 已核验；冻结源码 HEAD `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`。独立设计 SHA-256 与 manifest 中 `82af4bc4…fc06352` 一致。本轮仅审设计，不将 M0/M1运行PASS当成M2实现证据。

## 结论摘要

Codex 方案总体采纳独立方案的核心方向，并补足了我原先的未决项：M2-A 全量、不可变索引；独立 catalog/state machine；sealed input vector；pre/post manifest；失败保留旧索引；M2-B 以完整 per-TU artifact 复用并以 full shadow oracle 验证；负向 include 采用 namespace conservative invalidation；Diff 保留 uncertainty。没有发现会使 M2-A 架构必然错误的阻塞。

## 逐项比较

### 身份、快照、一致性

双方都明确区分 Git HEAD、磁盘 workspace snapshot 和 semantic index。Codex 进一步定义 repository/git/snapshot/index/build_profile，并规定 dirty workspace 的 HEAD 只是 provenance，不能冒充磁盘等于 HEAD；这正确回应了现有 `index.py:311-318` command/toolchain hash 与 `build_index:319-330` 直接分析输入的限制。

Codex 的 sealed copy、descriptor/hash 检查、pre/post manifest、修改后不发布，比独立方案的方向一致且更具体。其明确承认普通文件系统无法证明任意多文件瞬时一致，避免过度承诺。需实施时验证原路径映射、symlink policy、生成文件和 toolchain capture；这是前置验收，不是本轮架构阻塞。

### C++ 依赖与负向 include

双方都拒绝从 `unit_files` 推断完整依赖。现有 analyzer 只在 `main.cpp:258-268` 输出实际 SourceManager buffers，`index.py:60-64` 的 unit_files 不能表达失败查找、搜索顺序或 shadowing。Codex 明确引入 PPCallbacks/DependencyCollector，并承认 callbacks 不证明所有 candidate path probes；对新增/删除 namespace、include 顺序和无法捕获的 negative lookup 采用全量失效。这是正确的 fail-closed 边界。

接受的实现风险：必须把 `#include` 缺失后新增同名头、较早 `-I` 的 header shadow、`__has_include` 和宏/inline/template 修改做成真实 Clang 回归；不能把“collector 有记录”直接写成精确负依赖完成。

### 增量与发布

Codex 选择 M2-A 不复用、完整新索引；M2-B 只复用带 FactKey 的完整 TU bundle，再重新 aggregate/ODR/anchor validate，和独立方案一致。旧 aggregate 不拆分是重要正确性决定。catalog 的 `building/failed/ready`、CAS generation、single writer、crash recovery、lease/GC 比独立稿更可执行。

现有 `index.py:339-365` 只对新 DB 做临时文件+hard-link，不能承载 workspace attempt/catalog；Codex 没有误称现有实现已具备M2。建议实施保留 schema3 legacy readonly，并让 schema4/catalog 新路径原子迁移；不在查询连接中迁移。

### Schema 与 Diff

Codex 明确提出 schema4、离线新路径迁移、legacy index `not_comparable_legacy_index`，避免伪造旧索引 workspace identity。Diff 分离 symbol/relation/location/coverage/uncertain，保留 virtual/unknown；对现有 `instance_id`（`index.py:274-285`，包含位置和 expansion anchors）不做集合减法，而设计位置无关的唯一匹配并对重复站点标 ambiguous。这比只比较 USR/instance_id 正确。

实施风险较高但已明确：definition ranges、protocol3、call correspondence、failed TU 的“不删除”规则必须先实现并按 acceptance 逐项验证。若匹配不唯一必须输出 ambiguity，而不是用行号/ordinal 猜 target_changed。

### 成本、安全、验收

Codex 方案比独立稿更重：sealed captures、schema4、catalog、protocol3、full shadow validation、HTTP POST token/CAS、leases。但它把增量放到 M2-B，M2-A 保持可控；安全上没有开放任意路径或 project build，明确拒绝 response/unsafe flags，HTTP refresh 非 GET。

`acceptance.md` 分离 C/D/L/H/B 层，包含普通函数、目标变化、位置移动、header/macro/template、增删改名、TOCTOU、失败发布、schema迁移、negative include、token/CAS、cache corruption 等22组，且要求真实 Clang/CLI/HTTP/Chromium。这是可执行的验收框架，不是M2已通过的证据。

## 必须保留的前置门槛

无当前 NEEDS_CORRECTION 阻塞；但开始 M2-A 前必须冻结五项设计决定：sealed snapshot实现和权限/symlink语义、LLVM18 dependency/negative lookup捕获或保守全量规则、Git raw HEAD/profile策略、catalog crash recovery/lease/GC、protocol3 ranges与call correspondence规范。Codex 已把这些列为 open gates，不能在实施中默认省略。
