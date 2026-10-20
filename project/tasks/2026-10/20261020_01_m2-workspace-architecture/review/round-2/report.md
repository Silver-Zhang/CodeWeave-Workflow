# M2-R0 Round-2 独立设计审核报告

## 1. 对象与范围

本轮审核 Codex v2 完整 M2-R0 设计，不审核生产实现。候选 manifest raw SHA-256：`3e546ddd151ba17df2500ed930e0e2149f1ea314680651efc7124b7d075deb1b`；5个设计文件、62个冻结 M1 源文件均逐项 bytes/SHA/mode 核验通过。source HEAD：`6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`。源码、候选、旧任务和双方原文均未修改。

## 2. 做法与证据

我先独立完成方案，随后完整读取 v2 `architecture.md`、`acceptance.md`、`decisions.md`、`research-evidence.json`、`research_probe.py`，并对照冻结 M1 的真实调用链：Analyzer `main.cpp:90-104,148-182,258-268,318-337`；`index.py:93-112,179-205,224-290,319-373,463-578`；HTTP/CLI共享 query；前端历史 index/source/request 隔离。

本轮不把 M1 回归或 owned probe 当 M2 实现证据。research evidence 明确其 standard-header minimal view、owned escape和generic fresh-run只证明当前原语可行，不证明 production capture安全。

## 3. Findings与五项门槛

### F0：无阻塞 Finding

v2已解决第1轮要求的五项设计决定，且没有发现不可实施的核心矛盾。

1. **封存与权限已固定。** `architecture.md:47-56`规定 descriptor-safe sealed vector、pre/post hash、root不重叠、项目/依赖链接拒绝、toolchain alias逐链验证、最小 runtime ELF + frozen resource/header tree、无 live `/usr` fallback；标准头 positive、越界 owned include negative在`acceptance.md:24`。若未来实现无法收集合法toolchain，应显式unsupported，不可放宽安全边界。
2. **negative include已固定保守规则。** `architecture.md:100-115`承认 PPCallbacks不等于完整失败探测；namespace结构变化统一全量，read-set只用于内容变更的保守失效。新增 optional header、较早 include root shadow、`__has_include`在`acceptance.md:25`。不宣称精确最小集合。
3. **HEAD/profile已固定。** `base_git_head`、`represented_git_commit`、dirty/ignored input和raw Git tree分离（`architecture.md:38-45,58-64`）；profile包含命令、root mapping、toolchain/runtime和编译可观察 metadata。不会把当前磁盘或ignored compiler input冒充HEAD。
4. **发布/迁移/生命周期已固定。** Codex选择同一 schema4 SQLite 保存事实及workspace/attempt/catalog性质表，不是独立 catalog 文件；旧 schema3 新路径离线导入，query不迁移，失败attempt不改变 default，A不自动GC、B显式prune。`architecture.md:76-94`与`decisions.md:23`形成一致规范。接受该单库选择，前提是crash/ENOSPC/fsync与完整旧事实保持在实施验收中验证。
5. **protocol3/site配对已固定。** `architecture.md:195-202`要求AST/token路径、callee placeholder、macro structure、唯一一对一候选；重复/重排/不连续宏输出ambiguous/unmatched，绝不用ordinal/行号猜target_changed。relation multiset独立于location instance。`acceptance.md:9-15,21-23`提供正负oracle。

### F1：实施风险（非当前阻塞）

- Toolchain alias、descriptor安全复制、seal后的host编辑语义和SQLite单库崩溃恢复是高风险实现点；v2已给出失败关闭规则和具体验收，不再是未决定架构问题。
- Site correspondence可能在真实宏/重复调用中经常不可配对；这是可接受的明确不确定性，前提是实现输出ambiguous而不误报。unique `return alpha()`→`beta()`必须作为正例通过。
- 单 schema4降低跨文件catalog恢复复杂度，但会使迁移/写事务/读锁设计重要；要求离线新路径迁移、旧schema3 readers不变，未发现架构错误。

## 4. 唯一裁决与实施条件

**唯一裁决：ACCEPT（M2-R0设计审核）。`implementation_ready: true`，仅表示设计可进入 M2-A 实施，不表示 M2-A/M2-B已实现或通过。**

逐项判断：

- Workspace/Git/snapshot/index身份：PASS，需按v2 provenance实现。
- sealed capture、权限、toolchain最小视图、TOCTOU：PASS，需通过 acceptance 10/16。
- C++依赖、negative include、shadowing：PASS（保守全量失效）；精确增量尚未实现。
- schema3→schema4新路径迁移、单库原子发布、失败保留旧default、生命周期：PASS，需 crash/ENOSPC/restart实测。
- semantic Diff、definition ranges、location-vs-semantic、failed coverage、严格site correspondence：PASS，需 protocol3和adversarial tests。
- CLI/HTTP共享query、bounded output、显式refresh写安全、pair身份：PASS，需实现后HTTP/CLI/Chromium验证。
- M2-A与M2-B边界/验收：PASS；A为全量正确基线，B只能在A独立通过后以cache miss/full shadow equality进入。

开始 M2-A 前必须保留：普通标准头 minimal view正例、alias越界负例、负向include/early shadow、dirty ignored profile、sealed mutation、crash migration、duplicate call ambiguity等门槛。研究摘要不是实现PASS。

## 5. 过程

- 核验 v2 manifest与62源码身份。
- 全读 v2五个文件并依据冻结源码重审第1轮五门槛；按用户提醒纠正旧comparison的两个事实表述，不改旧原文。
- 写入 `comparison.md`、本 `report.md` 和 `result.json`；没有生产实现或Git操作。

已完整读取 `candidate/research_probe.py`，此前报告“完整读取五个文件”的表述现有实际证据支持。该脚本的预定义 oracle 在 `20-26` 明确写入五项期待：共享/宏头进入两个 TU read-set、optional header 改变目标、仅移动行保持外部 USR/关系多重集但 instance_id 改变、物理 root 改变影响内部身份、旧 index 保留源字节和 status。

脚本实际使用本轮传入的 `source-root`、新 analyzer、resource-dir 和自有 `--work`；`30-43` 通过独立公共 CLI 进程执行真实 index，`45-50` 通过 CLI query 读取事实。它创建自有 fixture/SQLite/日志，使用 `shutil.copytree` 复制到自有目录，不改生产源码、测试或既有 DB；没有事实注入或成功结果 mock。`53-77` 的 optional header、位置移动和调用目标均由真实 analyzer/SQLite 结果断言，`78-84` 检查物理 root 变化、旧 snapshot source/status；`84` 明确 scope 为当前 M0/M1 facts、不是 M2 实现验收。

脚本仍有一个设计层限制：它没有覆盖失败 include 的全部 candidate path probes、descriptor-safe capture、toolchain alias安全或负向 namespace invalidation；v2 架构和 acceptance 已将这些列为未来实现门槛，因此不改变本轮设计裁决。最终 5 个候选文件和 62 个源码文件再次逐项匹配 manifest；raw manifest SHA-256 仍为 `3e546ddd151ba17df2500ed930e0e2149f1ea314680651efc7124b7d075deb1b`，无错误。
