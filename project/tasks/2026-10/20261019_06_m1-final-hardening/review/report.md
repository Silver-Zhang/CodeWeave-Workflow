# CodeWeave M1-Final Round-1 独立审核

## 1. 目标与范围 / 对象身份

**唯一裁决：ACCEPT。** 建议用户批准本候选冻结；本审核未执行 Git 提交、推送、合并、发布或进入 M2。

本轮绑定完整候选 `/home/workspace/CodeWeave_dev/m1-final-hardening-20261019/round-1/candidate`，基线 HEAD `2d49db0e0b3d5e17cb95e9b876ffea0077e4ba8b`，分支 `feat/m1-interactive-map`。清单 raw SHA-256 为 `f0714eb0def67f241fc14a442465202fcbf170e5e224e6bd32837a8d7795998c`；62/62 文件的 bytes、SHA-256、mode 在审核开始和结束均核验一致，无候选变化。旧 M1 三轮报告仅作线索，本轮重新审核完整 M1 与 M1-Final refresh/performance 范围。

候选、旧任务、CodeWeave/DevFlower 源码均只读；所有审核 build、真实 fixture、SQLite、浏览器 harness 和日志位于本审核区。未读取 RMC、reference、F11、真实私有工程或凭据。

## 2. 做法与证据 / 实际命令

### 环境与全新构建

Python `/home/workspace/CodeWeave_dev/.venv/bin/python` 3.12.3、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0、Node22.23.3/npm9.2.0；resource dir 明确为 `…/llvm-18/usr/lib/llvm-18/lib/clang/18`，`include/stddef.h` 存在。由本轮候选全新构建 analyzer，SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`。

实际运行：

- `bash candidate/scripts/verify_m1.sh`，正确 Python/LLVM/resource/PATH，exit 0：后端 **110 passed**、0 failure/error/skip；fixture unittest 1/1；前端 type/build；Vitest **35/35**；真实 Playwright Chromium **7/7**。
- 正式验收日志中的真实 Clang、Bubblewrap、CLI、HTTP 和 Chromium 均来自本轮新 analyzer/build；未使用旧 binary。
- 完整回归涵盖 CLI/HTTP 同一 query/index_id/facts、status/search/show/calls/neighbors/source、虚/unknown、图预算/环/去重、快照切换、Unicode byte→Monaco UTF-16、旧 neighbors 延迟选择和本轮 refresh regressions。

### 独立真实 22-index catalog 变体

脚本 `catalog_real_check.mjs` 在本审核区新建自有目录，复制候选 `tests/fixtures/m1`，通过本轮新 analyzer、公共 CLI 和 Bubblewrap 连续发布 **22 个真实索引**，另发布一个新索引；HTTP 启动使用实际只读 SQLite，事实未手写。

预定义期待：初次 `/api/indexes?limit=20&offset=0` 应返回 20 项和 next page；加载历史页后选择早期历史索引，刷新期间释放延迟 page-0 response 并选择另一历史索引，不能丢选择或旧 source；新索引发布后刷新应出现新 option，但不得自动切换。

最终有效运行 exit 0：`catalog-real-check.log` 返回 `PASS`，`generated_count=22`，通过 `22-real-index-paged-history`、`refresh-manual-selection-race`、`new-real-publication-preserves-selection`。早期 harness 因两索引 fixture 无 `Load older indexes`、按钮前提错误及 Playwright route cleanup 错误失败，均保留且不算产品结论；最终变体修正为真实 22 索引后才计 PASS。

### 独立 neighbors 性能与只读证据

脚本方法先静态核对：`index.py:549-578` neighbors 通过共享 `query()`，每个 caller/callee 逐个 `show` 查询；连接使用 readonly URI，schema validation 使用独立 `:memory:` connection；查询后检查 persistent DB SHA、authorizer 写操作、响应字节和分页事实。

独立复测命令使用候选 backend、正确 Python、全新未预创建 work 目录、`--samples 7`，exit 0；原始结果：`performance-independent-1792395602104963335/results.json`。样本包括 synthetic fanout 1/5/12/25/50、cycles、moderate corpus，以及实际公共 CLI/新 analyzer/Bubblewrap 的 `real_clang_multifile`。

代表结果：fanout 1/5/12/25/50 的 persistent connections 为 4/8/15/28/53，persistent SQL 为 25/53/102/193/368，median warm-cache latency 为约 1.59/3.13/5.85/10.58/20.32 ms；返回实例和 page totals 正确，最大 JSON 31,469 bytes，write attempts 为空，DB hash 不变。该线性 N+1 是已量化的潜在扩展成本，但本轮没有无依据的硬毫秒阈值，也未证明影响 M1 正常使用；按合同记录为性能基线/后续优化建议，不是必需缺陷。性能数据中的 synthetic SQLite 明确不是 Clang 语义证据；真实多文件 case 只用于语义/只读对照。

## 3. 决策 / Findings P0-P3 / 关闭

### P2-FINAL-REFRESH-INDEX-CATALOG：CLOSED

`frontend/src/App.tsx:32-45,117-121` 通过 index request token、AbortController 和 functional state update 区分初次加载/刷新/分页；`setIndexId(current => current || page.index_id)` 只在无选择时自动最新。刷新 page 0 保留已加载历史 option；显式 index change 仍清空 graph/source/request；失败显示 JSON-derived error 和 Retry，不清空有效视图。真实 22-index Chromium 变体覆盖历史 page、重叠 refresh/manual selection、真实新 publication，最终通过。

### 性能 P2：基线而非缺陷

存在可复现的逐目标 `show` 查询增长，但当前实测小图和 UI limit 的 warm-cache 延迟约 1.6–6.1ms，响应/事实/只读保护正确；没有合同规定的性能失败阈值或大工程证据。建议后续在真实大索引上按 workload 再评估批量查询，不能把本轮 synthetic 结果包装成已优化或生产性能保证。

没有确认的 P0、P1 或其他必需 P2。曾有工具/环境错误均未计产品结果：错误 Python 路径 exit127；预创建 `--work` 与 `exist_ok=False` 冲突；auto classifier 拒绝删除动作；旧两索引 refresh harness 因不存在的 Load older 按钮及 route cleanup 失败；这些负日志均保留。

## 4. 唯一裁决、逐合同判定与限制

**ACCEPT。** 本轮证据充分且无未关闭阻塞。

- Refresh 历史选择、首次最新、历史分页保留、新 publication、显式切换清理、失败重试、异步竞态、空库：**PASS**（源码、110 backend/35 frontend、7 Chromium、独立真实 22-index Chromium）。
- CLI/HTTP 同一只读 query/index_id/facts、分页/预算/JSON 错误及快照：**PASS**。
- 本机 FastAPI host/origin/path/database 安全、不写索引、不执行编译：**PASS**。
- 真实 Clang/Bubblewrap 局部图、USR/instance 去重、循环、virtual/unknown、预算：**PASS**。
- UTF-8 physical byte column → Monaco UTF-16、节点/边 source 定位：**PASS**，并在完整真实 Chromium 中执行。
- neighbors 性能：**PASS（基线证据充分，记录 N+1 后续建议，不宣称优化）**。
- 新 analyzer、完整后端、前端 build/Vitest/真实 Chromium、零关键 Skip：**PASS**。

限制：结论绑定 62 文件候选与 Linux/LLVM18/Bubblewrap/Node22；不覆盖 PCH/modules、复杂全程序虚分派、M2 增量/Git diff、私有项目和大规模性能专项。性能复测为 warm-cache、本机、7 样本；synthetic case 不能代表 Clang 语义或生产规模。历史旧任务/报告未改写。

## 5. 过程

| 事件 | 结果 |
|---|---|
| 读取合同并建立独立 checklist；核验候选 | 62/62 文件一致，manifest `f0714eb0…99598c` |
| 全新 analyzer + 正式 verify_m1 | exit 0；110 backend、35 frontend、7 Chromium、fixture 1 |
| 初始 refresh harness | 失败，因只发布两索引且等待不存在/禁用的分页按钮；另有 Playwright route cleanup 问题；未计产品结论 |
| 22-index 真实 catalog harness | 真实 CLI/Clang/Bubblewrap/HTTP，最终 exit 0；历史分页、重叠刷新、新 publication PASS |
| 性能独立复测 | 先保留错误 Python/预创建目录/auto拒绝日志；随后正确 Python、全新目录、7样本 exit 0；结果和只读/预算证据已记录 |
| 结束复核 | 候选身份仍 62/62 一致；未改候选、未 Git 交付、未访问私有项目 |
