# M2-R0 独立架构设计：Workspace Snapshot, Incremental Indexing & Semantic Diff

> 本文件是独立设计，不是生产实现、不是 Codex 方案审核，也不是 M2 ACCEPT。依据冻结 M1 `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7` 的源码和 `requirements.txt`；生产源码未修改。

## 1. 当前事实与约束

### 1.1 身份边界

M1 目前只有三类可观察身份：

1. **文件快照事实**：Analyzer `main.cpp:110-113,258-268` 对每个 Clang buffer 记录 path、sha256、项目内容或外部依赖哈希；`index.py:231-243` 将同一路径不同 bytes 的跨-TU观察拒绝为 `inconsistent_input`。
2. **编译/TU身份**：`index.py:179-205,311-318` 由 canonical source、normalized arguments、toolchain 和 command digest 建立 units；M1 schema 3 的 `units` 保存 command 与 diagnostics（`index.py:56-64`）。
3. **索引发布身份**：`index.py:334-373` 生成 UUID，在新库临时文件完成事务后用 hard-link 发布；失败不改变旧库。查询以显式 `index_id` 选择历史 snapshot（`index.py:375-379,478-483`）。

M2 必须再引入而不混淆：

- `workspace_id`：受信本地工作区配置身份，不是路径字符串本身。
- `workspace_snapshot_id`：某次显式采集的**磁盘状态**身份。
- `git_commit_id`：被 Git 解析的 commit SHA，仅在 clean/指定 commit 内容下成立。
- `semantic_index_id`：对某个 snapshot + compilation profile + analyzer/protocol/schema 身份成功发布的不可变事实快照。
- `refresh_attempt_id`：失败或运行中的尝试，不能成为可查询默认 index。

编辑器未保存 buffer 不属于 M2 输入；只能提示“磁盘状态可能落后”，不能把内存文本写入 snapshot/index。

### 1.2 M1 的重要可复用点与缺口

- 真实分析器没有输出显式 include/import dependency graph；只输出 `file` records（`main.cpp:258-268`），而 `unit_files` 是分析后观察到的 file association，不足以安全判定“未变化 TU 可复用”。
- Analyzer 直接枚举 compile database 的 TU（`main.cpp:318-320`），并在 `SourceManager` 结束时记录实际打开的 files；可作为依赖事实的基础，但需要在 M2 增加受信的 include-trace/CompilerInvocation 依赖捕获或另一个确定的 Clang callback，不能从 `unit_files` 猜 header dependency。
- `build_index()` 在分析前读取 ccdb，分析时可能读取不一致文件；现有跨-TU冲突能拒绝混合 buffer，但不能给出整个 workspace 的统一 generation。M2 必须在采集和发布处加入一致性验证。
- current `_collect` 只接受 unit status `complete`（`index.py:244-249`）；因此失败尝试整体失败并保留旧 database 是可复用的安全基线。
- M1 query 全部 readonly，schema 验证连接是独立 `:memory:`（`index.py:93-112`）；M2 写操作不得进入 query/HTTP GET 路径。

## 2. 推荐总体架构

### 2.1 M2-A：先全量、正确、不可变

M2-A 不做增量事实层：每次用户明确 `Refresh Workspace` 都执行全量安全重建，产生新的 immutable `semantic_index_id`；旧 index 永远保留。M2-B 之后才允许复用。

组件分层：

```text
WorkspaceConfig (trusted startup path/profile)
  -> SnapshotCollector (Git + filesystem + ccdb fingerprints)
  -> ConsistencyGuard (pre/post manifest; retry/abort on change)
  -> Full Analyzer / Bubblewrap (same source generation)
  -> Staged immutable index database
  -> Validator (facts/schema/identity/diff metadata)
  -> atomic publish pointer/catalog transaction
  -> shared query/HTTP/CLI (read-only by default)
```

推荐用 workspace 数据目录，而不是让现有单个 `index.sqlite3` 同时承载可变工作区和历史：

```text
workspace-root/.codeweave/
  workspace.json
  snapshots/<snapshot_id>/manifest.json
  indexes/<semantic_index_id>.sqlite3
  indexes/<semantic_index_id>.meta.json
  catalog.sqlite3                 # trusted local control/catalog, not facts
  current                    # atomic text pointer or catalog row
  attempts/<attempt_id>/...
```

对共享目录必须更严格：workspace metadata/catalog/attempt dirs 由启动配置建立，不能从 HTTP path 参数选取；只有显式 CLI `workspace refresh` 写入。旧 M1 `--database` 查询继续只读兼容。

### 2.2 SnapshotCollector 与一致性

一次 refresh 先获取 `pre_manifest`，再分析，最后获取 `post_manifest`。manifest 对每个输入保存：canonical path、`lstat`/symlink policy、size、mtime_ns（诊断用，不作唯一身份）、sha256、kind（project/dependency/toolchain）、Git path/status、rename candidate；对 compile database 保存 bytes hash；对 profile 保存 normalized command hashes、resource/toolchain/analyzer/protocol/schema hashes。

流程：

1. 解析受信 workspace root；拒绝 root 是 `/`, home, `/tmp` 等 host-wide 根，沿用 `_trusted_root` 规则。
2. 读取 Git HEAD、`git diff --name-status -z` 和 `git ls-files -z --cached --others --exclude-standard`，但 Git 命令只在受信 workspace collector 进程中运行；Git 不提供未跟踪 ignored 文件的授权，manifest 仍只覆盖显式授权 source/ccdb/dependency roots。
3. 对 compile database 做 JSON parse + normalized commands；记录 source list，先收集所有 source/header candidates；禁止执行 project build scripts。
4. 为每个 source/config 建物理哈希。使用 `openat`/`O_NOFOLLOW` 或等价 realpath + post-open identity检查；拒绝 symlink escape。读取文件必须来自同一个 collected manifest generation。
5. pre manifest 完成后，把分析输入放到 snapshot staging area：项目源码只读 bind；ccdb 的 staging copy 与 snapshot manifest 固定。Analyzer 仍在 Bubblewrap 内运行。
6. 分析结束再计算 post manifest。任何受关注文件 hash、ccdb bytes、Git HEAD、profile 或 authorized path set 改变，整次 refresh 标为 `stale_during_refresh`，不发布，也不混用部分结果；默认最多一次自动重试，仍变化则失败并保留旧 index。
7. 还应在 analyzer 每个 TU 的 facts 中验证 file sha256 与 pre manifest；已有 `_collect` 继续作为最终防线。对于 TOCTOU 无法通过普通 hash完全消除的系统，使用只读 snapshot copy/bind mount 作为分析实际输入，而不是直接读活动工作区。

Git clean commit 的 `git_commit_id` 只有当 Git tree 与 manifest 完全一致时才填 commit SHA；dirty workspace 仍记录当前 HEAD 作为 `base_git_commit_id`，但 `git_commit_id=null`，并设置 `workspace_dirty=true`。重命名由 Git status 记录和 hash pairing 作为 metadata；语义层仍按 old/new path 与 USR 分开判断，不能因 rename heuristic 直接证明符号不变。

### 2.3 捕获 header/include 依赖与负向依赖

M2-B 的依赖关系必须来自实际编译配置和实际 preprocessor resolution，而非只看 `#include` 文本。

对每个 `(tu, command_digest, toolchain_digest, snapshot_generation)` 保存 `tu_inputs`：

- canonical resolved path；file sha256；scope project/dependency/toolchain；
- include edge parent→child（含 include spelling、resolved physical path、include depth/order 可选）；
- macro/config profile digest；compiler resource dir and relevant builtin headers；
- unresolved include records / diagnostic status；negative lookup records（尝试过的 include directories/name combinations），至少保存足够信息证明 new header shadowing。

推荐实现顺序：

- M2-A：先不复用，只保存 actual `file` records 与 manifest。
- M2-B v1：用 Clang preprocessor callbacks/`SourceManager` file entries 记录实际进入的 file、spelling parent、resolved path；用 Clang `PPCallbacks::InclusionDirective` 和 file-enter/file-exit 建立正向 dependency edges。
- M2-B v2：为每个 include resolution 保存 include search profile（目录顺序、framework/system/resource roots）和 negative lookup fingerprint。若无法获得可靠 negative lookups，任何 include path set / new file / delete/rename / compiler macro change 都升级为全量；不要宣称精确增量。
- 预compiled/module/header cache、implicit builtin and command-generated headers 在 M2-A 全量模式不复用；M2-B 初期遇到 PCH/modules/generator output 一律 invalidate-all 或不支持。

失效算法：

```text
changed_direct_inputs = changed source files + changed ccdb/profile/toolchain files
changed_headers = changed resolved inputs + added/deleted/renamed candidate paths
for each TU:
  invalidate if TU source/config changed
  or any resolved dependency hash changed
  or any dependency's transitive reverse edge changed
  or include search order/root/macro/resource/toolchain changed
  or negative lookup fingerprint may change
  or prior TU/index status was failed/incomplete
if dependency capture incomplete or snapshot generation differs: full rebuild
```

负向 include 例：TU has `#include "new.hpp"`, old snapshot resolves none and emits error; adding `src/new.hpp` can change resolution even though no old `tu_inputs` path exists. Therefore a changed/new/deleted project path matching an include basename in any include search root invalidates all affected commands, or full rebuild if negative index unavailable. A new header earlier in `-I` order can shadow an unchanged header: include directory order/config digest change invalidates all affected TUs.

Macro/inline/template changes invalidate every TU whose actual dependency closure includes the header; macro command-line change invalidates every TU using that profile, and conservative profile-level invalidation is acceptable. `.cpp` change invalidates its TU; deletion removes it from next snapshot only after full analysis success.

### 2.4 Reuse model for M2-B

Do not copy individual symbols/calls into the live old DB. Store per-TU fact bundles in a content-addressed cache keyed by:

```text
FactKey = hash(analyzer_sha, protocol, schema, normalized_command,
               resource/toolchain digest, TU source sha, complete dependency closure,
               dependency capture version, snapshot policy)
```

The authoritative published index is still a complete materialized immutable snapshot. Reuse means loading verified bundles for non-invalidated TUs into a new staging DB, then running the same cross-TU `_collect`/merge/conflict/foreign-key validation as full build. If bundle missing, stale, dependency capture incomplete, or cross-TU declarations/definitions conflict, recalculate affected/full; if full fallback cannot verify, do not publish.

This preserves M1 `indexes/files/units/symbols/calls` query behavior and lets old `semantic_index_id` remain immutable. Cache entries are disposable and never exposed as public index identities.

## 3. Atomic publication, failure and schema

### 3.1 Catalog and state machine

Use a small schema-versioned `catalog.sqlite3` or manifest-plus-atomic-pointer. It stores:

- workspace config and trusted root identity;
- snapshot rows: `snapshot_id`, parent/base Git SHA, workspace dirty flag, pre/post manifest SHA, capture timestamps, consistency state;
- index rows: `semantic_index_id`, snapshot_id, profile/toolchain/analyzer/protocol/schema digests, state (`building`, `ready`, `failed`, `stale`, `retained`), DB path, row counts, error code;
- current/default pointer and retention metadata;
- diff records are derived or separately versioned by pair, never mutable facts.

Schema 3 fact DB remains readable and immutable. Do not silently mutate schema 3 in place. If a new column/table is needed for M2 metadata, use schema 4 migration in a new database/catalog or a new `.sqlite3` file; keep a tested explicit migration/import path. Prefer catalog v1 + unchanged per-index schema 3 for M2-A, delaying fact schema change until a concrete query needs it.

Refresh transaction:

1. Create `attempt_id`; state `building`; never touch current pointer.
2. Build staging fact DB in a new temp directory and validate schema, facts, snapshots, command/profile identity and pre/post consistency.
3. `fsync` DB and directory; close connections.
4. Atomically rename staging DB to immutable `indexes/<id>.sqlite3` (same filesystem), then transactionally mark index `ready` and update current pointer. Use a single catalog transaction with explicit ordering; on crash, startup reconciles ready DB/catalog rows and removes only unreferenced building artifacts.
5. Query default chooses catalog current ready ID; explicit historical ID remains available.

Existing M1 publication uses `os.link(temporary, database)` (`index.py:341-365`), which is safe for a new path but is not a workspace catalog and cannot by itself represent failed attempts, dirty identity, dependency metadata or retention. M2 should not overwrite a live file.

Refresh failure categories: `input_changed_during_refresh`, `ccdb_invalid`, `analysis_failed`, `inconsistent_input`, `conflicting_definition`, `schema_error`, `publish_error`, `cancelled`. Every failure stores diagnostics and attempt manifest; current ready index remains queryable. Never delete last good index on failure.

Retention: keep current, selected/pinned, and a configurable recent N; garbage collection only catalog-referenced unpinned immutable DBs, after closed connections and atomic catalog update. Never GC an index selected by an active UI request without leases/reference counts.

## 4. Semantic diff and shared bounded API

### 4.1 Version pair and uncertainty

A diff request names `base_index_id` and `target_index_id`; both must be ready and from compatible workspace/profile unless explicitly marked incomparable. A pair result has `diff_id`, source identities, analyzer/protocol/schema/profile digests and coverage/uncertainty summary.

Symbol identity uses semantic USR plus M1 local identity rules. For local/static symbols the current USR is decorated with file/TU (`main.cpp:90-103`), so a path rename appears as remove/add unless a separately reported file identity/hash rename heuristic matches it. Never silently merge those identities. Overloads remain distinct USRs.

Define separate change sets:

- `symbol_added`, `symbol_removed`, `symbol_modified` (definition/declaration/ODR hash/signature/kind/name), `symbol_moved` (same semantic identity, changed anchor only), `symbol_uncertain`.
- `call_added`/`call_removed` keyed by `(caller_usr,target_usr,dispatch,instance_id)`; `call_instance_moved` when same instance semantic fingerprint has changed location; `call_target_changed` only when caller/source call identity is matched and target differs.
- `unknown_added/removed/changed` preserves `unknown-function-pointer`/`unknown-dependent`; never converts unknown to a proven direct/virtual edge without target fact.
- `compile_failed`, `unit_missing`, `coverage_regressed`, `input_changed` are first-class status, not symbol removals.

Because M1 call instance ID hashes full location/spelling/expansion chain (`index.py:274-285`), source line moves change the ID. Diff should compute a secondary matching fingerprint excluding physical position but including caller, target, dispatch, spelling identity/normalized token or anchor content hash, expansion chain identity, and TU/config. Matching is heuristic and must be reported `match_method=location-independent-heuristic`; if ambiguous, retain add/remove plus uncertainty. Pure line movement is `moved`, not semantic call add/remove, only when match confidence is unique.

Compare snapshots with same workspace/profile. If a TU failed in target, symbols/calls from that TU must not be declared removed: emit `coverage_regressed`/`unit_failed` and mark affected removals `uncertain` or omit them. A symbol present only in a dependency whose version changed similarly carries input provenance. Diff output is bounded/paged and includes both index IDs, exact source paths/anchors, snapshot hashes, evidence and uncertainty.

### 4.2 CLI/HTTP contract (design only)

Extend the same query kernel; no second parser or frontend fact model.

Minimal commands:

```text
codeweave workspace status --workspace <trusted config>
codeweave workspace refresh --workspace <trusted config> [--full|--incremental]
codeweave query indexes --workspace <trusted config> [--limit N --offset N]
codeweave query diff --database/catalog <trusted path> --base-index ID --target-index ID [--kind symbols|calls|all --limit N --offset N]
```

HTTP GET remains readonly and bounded:

- `GET /api/workspace/status?workspace_id=...` (or fixed server workspace; no client filesystem path);
- `POST /api/workspace/refresh` only on explicit local action, CSRF/origin/host checked, returns attempt ID and bounded state; no refresh on GET;
- `GET /api/indexes`, `/api/diff?base_index_id=&target_index_id=&kind=&limit=&offset=`;
- `GET /api/changed-symbols`, `/api/changed-calls` may be aliases to bounded diff.

All responses include explicit identities, `returned_count/total_count/remaining_count/has_more/next_offset` and serialized-byte budget. Source always uses explicit index ID. HTTP write endpoint must be disabled by default or require local same-origin and an explicit server policy; it must never accept arbitrary DB/root path or run a project build command. CLI refresh is the primary M2-A write interface.

Frontend M2 only displays real API records: version pair selector, workspace state, refresh attempt progress/error, changed symbol/call list, and source at either explicit snapshot. It must clear/abort pair-specific state when either ID changes and never label a disk path as HEAD unless identity says so.

## 5. M2-A / M2-B implementation boundary and executable acceptance

### 5.1 M2-A: correctness baseline, full rebuild

M2-A production scope:

- trusted workspace config and explicit refresh;
- filesystem/Git/ccdb pre/post manifest and consistency failure;
- full reindex into immutable new schema-3 fact DB;
- catalog state machine/current pointer/history/retention metadata;
- workspace/index status and bounded historical index API;
- pair semantic diff over two ready full indexes;
- no fact reuse, no background watcher, no browser auto-refresh.

M2-A must not include a fake incremental mode. `--incremental` should either be absent or explicitly return `incremental_unavailable` until M2-B.

### 5.2 M2-B: dependency-aware incremental

Only after M2-A full-vs-full correctness is established:

- actual include dependency capture with positive and, where supported, negative resolution evidence;
- FactKey cache and reverse dependency graph;
- invalidation closure and conservative fallback-to-full;
- materialized full snapshot from reused verified TU bundles;
- measured speedup against M2-A full rebuild on real self-owned projects;
- exact equivalence test against fresh full rebuild for every supported profile.

### 5.3 Acceptance matrix

Every row runs on a fresh owned project, records pre/post manifests, snapshot/index IDs and exact API/CLI assertions:

| Case | Required expectation |
|---|---|
| ordinary function body edit | new snapshot, old index unchanged, symbol ODR/change shown |
| call target edit | old/new call instance/target diff exact; static relation not runtime trace |
| line-only move | moved/location change separate from semantic add/remove |
| shared header edit | M2-A full sees all affected TU facts; M2-B invalidates reverse closure |
| macro definition edit | all profile/closure-affected TUs invalidated; config identity recorded |
| inline/template edit | dependent TUs changed; no unsafe reuse |
| add/delete/rename source | manifest/Git status accurate; no stale source exposed; rename heuristic uncertain if needed |
| compile DB/flags/resource edit | profile digest changes; no old fact reuse |
| 22+ historical indexes / retention | pagination/history/current pointer stable; failure retains old current |
| pre-existing missing include then add header | negative lookup triggers invalidation/full fallback |
| new earlier include root shadows header | include search order invalidates affected TUs |
| mid-analysis source/header/ccdb edit | post-manifest detects stale; no publication; old index remains |
| one TU compile failure | attempt failed/coverage regressed; old index remains; no false removals |
| full refresh crash/publish failure | staged orphan recoverable; current ready index queryable |
| HEAD vs dirty workspace | `git_commit_id` null for dirty; base HEAD and workspace snapshot explicit |
| overload/static/rename | USR/local identity and uncertainty preserved |
| recursive/virtual/unknown calls | instances/dispatch preserved; no runtime claim |
| non-ASCII/CRLF source location | raw bytes, UTF-16 UI conversion, snapshot identity exact |
| source/database escape | no unauthorized path, no project command execution, readonly query hash unchanged |
| M2-B equivalence | incremental materialized index byte/fact/query equivalent to fresh full rebuild for supported cases |

Evidence classes must be separate: real Clang integration, DB/catalog contract, public CLI/HTTP, Chromium UI. Any unsupported dependency capture case is a conservative full rebuild, not a silent pass.

## 6. Risks, decisions and open questions

### Decisions

- Freeze immutable full snapshot + explicit catalog in M2-A; do not mutate schema-3 fact DB or build a live incremental facts table.
- Use pre/post manifests plus read-only staging copy to solve workspace TOCTOU; fail closed on change.
- M2-B reuse only verified per-TU bundles keyed by complete dependency/config/toolchain identity; materialize and validate a complete new index before publish.
- Treat missing include/negative lookup and PCH/modules conservatively; full rebuild/invalidate-all until evidence is available.
- Keep API/CLI/query facts shared and bounded; writes are explicit CLI refresh, not GET.

### Open questions requiring design gate before implementation

1. Which Clang callback/API and output schema provides complete negative include lookup evidence for the supported LLVM 18 build? If unavailable, define documented conservative invalidation.
2. Snapshot copy strategy: filesystem snapshot mechanism versus per-file immutable copy; benchmark disk cost and symlink/permission semantics.
3. Git command policy: whether to permit `git` subprocess only in a trusted collector and how to handle sparse checkout/submodules/ignored generated headers.
4. Catalog placement and crash recovery: catalog SQLite versus atomic pointer, and exact fsync/lease/GC protocol.
5. Definition of stable location-independent call-instance matching and confidence thresholds; ambiguous matches must remain uncertain.
6. Whether schema 4 is needed after M2-A API is finalized; default is no fact schema change until required.

**Design readiness:** M2-A is implementation-ready after the five open gates are decided; M2-B is intentionally not implementation-ready until dependency/negative-lookup capture is prototyped and equivalence-tested.
