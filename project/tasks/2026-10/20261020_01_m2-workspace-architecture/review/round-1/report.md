# M2-R0 独立设计审核报告

## 1. 目标与对象身份

本轮审核 Codex M2-R0 架构设计，不审核或声称 M2 生产实现通过。Codex候选 manifest raw SHA-256：`cc262acf82254468f3ff3e2652fdb974e419a0db822a28ae23ee6f489deb0a59`；3个设计文件、62个冻结 M1 源文件均已逐项核验。源码 HEAD：`6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`。独立设计文件 SHA 与候选 manifest 记录一致。生产源码、既有测试、双方方案均未修改。

## 2. 做法与证据

先阅读需求、冻结 M1 的 analyzer/backend/HTTP/CLI/frontend/代表测试，再完成独立设计；随后阅读 Codex 完整 `architecture.md`、`acceptance.md`、`research-evidence.json`，按源码调用链逐项对比。关键源码依据：

- Analyzer `main.cpp:90-104` 的 USR/TU-local identity，`148-182` 的 call anchors/dispatch，`258-268` 的实际 SourceManager buffers，`318-337` 的逐 TU 分析和失败状态。
- `index.py:47-91` schema3、`93-112` readonly/schema-memory连接、`179-205` ccdb normalization、`224-290` facts merge/anchor/conflict、`319-373` staging/transaction/hard-link publish、`463-578` shared bounded query/neighbors。
- HTTP `app.py:16-113` 受信 DB 与 readonly query adapter；CLI `cli.py:30-67` 受信启动参数和同一 query；前端只消费明确 index_id 的真实 API。

当前原语研究摘要只证明现有 M1 原语和 owned mount probe，不证明 M2 已实现；本报告没有把它当实现验收。没有访问私有项目。

## 3. Findings、决策与关闭状态

### F0（阻塞）：无

未发现 Codex 方案在 M2-A 方向上存在必须先返工的自相矛盾。其全量基线、sealed capture、不可变 index、独立 catalog、失败保留旧 index、schema4离线迁移、uncertain Diff 和 M2-B fallback 方向与源码约束一致。

### S1（实施前门槛，P2设计风险）：sealed capture 与 toolchain边界

**位置：** `architecture.md:47-56`、`acceptance.md:18`。**触发反例：** 分析期间修改共享 header、同尺寸内容 ABA、resource/toolchain live `/usr` header 改变、symlink/FIFO/生成头出现。**影响：** 若实施退化为 live bind/stat-only，两个 TU 可能读到不同版本，或缓存声称可复用却使用新头。**当前判断：** 方案已明确 sealed bytes、descriptor/hash、pre/post、失败关闭和 toolchain immutable generation；不是当前阻塞。**实施要求：** 在 M2-A acceptance 真实验证 sealed input、host mutation、symlink/type rejection、toolchain search-root confinement；失败不得发布。

### S2（实施前门槛，P2设计风险）：negative include 与 shadowing

**位置：** `architecture.md:96-115`、`acceptance.md:17`。**触发反例：** 旧版本 `#include "optional.hpp"` 未找到，刷新前新增该头；或 `-Iearly` 新增同名头遮蔽旧目录；或 `__has_include` 结果变化但旧正向 read-set不变。**影响：** 仅依 unit_files 会错误复用未变 TU。**当前判断：** Codex 明确承认 PPCallbacks 不证明所有 candidate probes，采用全 namespace inventory/保守全量失效，并规定不完整 capture 为 full rebuild/cache miss；设计正确。**实施要求：** LLVM18 实际 callback/namespace inventory 原型必须先过；否则不提供“精确增量”，统一全量。

### S3（实施前门槛，P2设计风险）：跨版本 call instance correspondence

**位置：** `architecture.md:117-139`、`acceptance.md:10-14`。**触发反例：** 同一函数内两个文本相同的 `target()` 调用交换/重复，或只插入行导致现有 location-based instance_id 全变。**影响：** 用 ordinal/line proximity 会把 target_changed 误报给错误 site。**当前判断：** Codex 要求位置无关 secondary fingerprint、唯一一对一匹配、重复时 ambiguous，并将 protocol3/range/correspondence作为 M2-A任务；设计可实施但难点已正确暴露。**实施要求：** adversarial duplicate/macro tests；匹配不唯一只能 ambiguity，不得 ACCEPT target_changed。

### S4（建议，P3）：M2-A范围较重

Schema4、sealed copies、catalog/CAS、protocol3、HTTP POST token、leases、双侧 UI 使方案成本高。该成本由安全/身份需求支撑，且 Codex明确 M2-A不做增量复用，未形成过度架构阻塞。建议按 M2-A vertical slices 交付，先 CLI/full snapshot/catalog/diff，再 HTTP/UI；M2-B 不提前实现。

## 4. 唯一裁决、逐项合同与限制

**ACCEPT（设计审核）。** 这只表示 Codex M2-R0 方案具备进入 M2-A 实施设计门的条件；不表示 M2-A/M2-B 已实现、已构建、已通过真实 Clang/HTTP/Chromium，也不表示生产源码可提交。

逐项判断：

- Workspace/Git/snapshot/index 身份：**PASS，待实施门槛验证**。
- pre/post consistency、sealed bytes、失败保留旧 index、原子发布：**PASS，待真实 TOCTOU/crash 验收**。
- C++ dependency、negative include、shadowing：**PASS（保守失效设计）；精准增量尚未实现**。
- schema3 legacy/schema4迁移：**PASS，要求新路径离线迁移和 legacy not-comparable**。
- semantic Diff、位置移动、call correspondence、unknown/virtual/failed coverage：**PASS，需 protocol3和adversarial acceptance**。
- bounded shared CLI/HTTP、readonly query、显式 refresh write security：**PASS，HTTP POST token/CAS需实现后验证**。
- M2-A/M2-B边界和22组验收：**PASS，可执行；当前仅设计合同**。

限制：本轮没有实现 M2，没有运行 M2 refresh/diff/cache；现有 research evidence 只支持当前 M1 原语。M2-B 只有在 dependency capture、negative lookup策略和 incremental-vs-full shadow equality 实施后才可进入独立审核。建议冻结的是 R0 设计、不是 M2 功能或生产分支。

## 5. 过程

1. 核验 manifest raw SHA、3设计文件和62源码文件；发现初次读取设计路径错误（候选文件位于 round-1/candidate），随后按准确路径完整读取，未将该环境错误当技术结论。
2. 读取需求和冻结 M1 源码，形成独立设计与检查标准。
3. 阅读 Codex完整 architecture/acceptance/research evidence，对比身份、依赖、发布、schema、Diff、安全、成本和验收。
4. 写入 `comparison.md` 与本 `report.md`；未修改候选、生产源码、测试、旧任务或 Git。
