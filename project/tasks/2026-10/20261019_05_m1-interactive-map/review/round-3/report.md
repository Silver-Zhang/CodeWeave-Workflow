# CodeWeave M1 Round-3 独立审核

## 1. 目标与范围

**唯一裁决：ACCEPT。建议用户可批准 M1 候选冻结；本审核未执行冻结、提交、推送、合并、发布或 M2。**

本轮是对完整新候选的独立审核，不复用 round-2 `ACCEPT` 或历史 M0 结论。

- 候选：`/home/workspace/CodeWeave_dev/m1-interactive-map-20261019/round-3/candidate`；基线 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`；分支 `feat/m1-interactive-map`。
- 清单 raw SHA-256：`fed1b6fe54a7844bd23e812182dafc54da79bd9ac19b404f37ce7d3659d6108e`。
- 开始和结束均核验 60/60 文件的 bytes、SHA-256、mode，均无错误。候选只读；build、fixture、数据库、浏览器脚本和日志均在 `claude-artifacts/review/round-3`。
- 审核范围包括完整 M1 合同、R1 Unicode 定位关闭无回归以及本轮新增的延迟 neighbors 导航时序问题。先建立 [`checklist.md`](checklist.md)，再读全候选源码和设计时序反例；未以实施报告或旧审核结论替代本轮实证。

## 2. 做法与证据

### 环境、源码调用链与独立构建

- Python 3.12.3、CMake 3.28.3、GNU C++ 13.3、LLVM/Clang 18.1.3、Bubblewrap 0.9.0、Node 22.23.3/npm 9.2.0；resource dir 明确为 `…/llvm-18/lib/clang/18` 且 `include/stddef.h` 存在。
- 从 round-3 候选新建 `builds/analyzer`：exit 0，analyzer SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；未复用旧 binary。
- HTTP 继续用 FastAPI 到 M0 `query()` 的单一 readonly SQLite 核心；受信启动 DB、host/origin/path/error/预算边界及 CLI/HTTP 事实结构未被本轮破坏。
- `frontend/src/App.tsx:73-84` 为每次 expansion 递增 epoch，旧 response 在 token 不相等时丢弃；而且非-reset expansion 仅 merge facts、不会调用 `select(entity)` 覆盖期间较新的 node/call-site selection。`App.tsx:38-45` 的 index switch 清空图/selection/source 并 abort 请求。USR/instance 去重、图预算、unknown/virtual 表示仍在 `graph.ts` 与相同 M0 facts 上。
- R1 Unicode 修复仍在 `SourcePanel.tsx:17-22`/`sourceLocation.ts`：保留 raw Clang byte provenance，转换 Monaco UTF-16 position，处理 LF/CRLF/CR。

### 真实命令与结果

| 验证 | 结果 |
|---|---|
| 新 CMake configure/build | exit 0；`cmake-*.log`、`analyzer-sha256.txt` |
| `CODEWEAVE_LLVM_PREFIX=… CODEWEAVE_RESOURCE_DIR=… PYTHON=… bash scripts/verify_m1.sh` | exit 0；真实 Clang/Bubblewrap 后端 **110 passed**、零 failure/error/skip（1 条既有 Starlette 弃用 warning）；fixture unittest 1/1；Node22 build；Vitest **27/27**；真实 Playwright Chromium **4/4** |
| 审核自有 Chromium `navigation_race_check.mjs` | exit 0；使用候选新 analyzer、真实 fixture SQLite/HTTP/生产 frontend，route 仅延迟 pong neighbors 后 `continue()` 原响应；验证 late expansion 不覆盖较新的 **call-edge** source/evidence selection，随后 index switch 清除旧图/editor；见 `navigation-race-check.log` |
| 结束候选复核 | raw manifest 与指定值一致、60/60 文件一致；`candidate-identity-after.json` |

自主时序反例预定义的期望为：旧 pong expansion 等待期间，用户选择 ping 的真实 call edge 后，释放旧 HTTP response 不能让 selected/source/evidence 或 source heading 退回 pong；再切换新 index 必须清空旧图/editor。该用例不 mock facts，所有 API 响应经 `route.continue()` 原样来自真实 SQLite/HTTP；实际 PASS。

审查自身浏览器 harness 有三次早期失败，均不是产品结果：React Flow locator strictness、Playwright route double-handle、当前 Playwright Route 无 `isHandled()` API。仅更正审核脚本的 locator/route handling，候选未改；最后真实时序用例 PASS，早期负日志保留。

## 3. 决策记录

### R3 navigation race

Codex 提供的旧反例是线索而不是本审核实测结论。本轮独立源审发现历史问题的根因确实会来自完成 expansion 后无条件选择其 entity；当前 `App.tsx:80-81` 已仅在 reset 时选择，保留较新的交互选择，且 epoch 继续抑制任何过期请求。

候选自身真实 Chromium 回归延迟 pong neighbors、再选择 ping node 后通过。审核自有变体更严格：延迟 pong response，期间点击真实 ping **edge**，检查 source heading 及 old index，释放 response 后仍是相同 edge/source/index；然后切 index 并检查旧 graph/editor 消失。该独立实际反例通过，因此此问题 **CLOSED**。

R1 `M1-R1-P2-UNICODE-MONACO-COLUMN` 仍 **CLOSED**：round-3 全验收的 Unicode/Monaco E2E 通过，转换层仍保留 raw byte columns。未发现新 P0/P1/P2/P3。

Vite 仍提示 lazy Monaco chunk 约 694.66 kB gzip 超过其建议阈值；该编辑器按需加载，不是无界图、隐私或正确性失败，作为非阻塞工程限制保留。

## 4. 结论与边界

**ACCEPT。** 当前固定 round-3 候选完整满足 M1 必需合同，且独立构建/真实 Clang-Bubblewrap/HTTP/Chromium 证据充分：统一事实和 index identity、只读本机 API、安全/预算/错误、局部静态图和未知/virtual 语义、USR/instance/环/预算、快照源码、Unicode editor 坐标、索引切换与延迟交互均有效。

- CLI/HTTP 同一 query/index_id/facts/source snapshot：**PASS**。
- FastAPI 本机 readonly、JSON errors、分页/预算、host/origin/path 安全：**PASS**。
- React 真实局部图、身份去重、unknown/virtual、环/展开收起/预算：**PASS**。
- 精确 node/edge source 导航、Unicode/CRLF byte→UTF-16 转换：**PASS**。
- 异步 neighbors 完成后的新 selection/source/index 不串用：**PASS**。
- 全新构建和完整真实浏览器验收：**PASS**。

结论只适用于该候选清单及 Linux/LLVM18/Bubblewrap/Node22 环境。M1 仍不声明 PCH/modules、复杂全程序虚分派、大仓性能优化、M2 工作区增量/Git diff 或私有项目覆盖。冻结、提交、推送、合并和发布均由用户另行决定。

## 5. 过程记录

| 时间 | 事件 |
|---|---|
| 2026-10-19 | 阅读合同、建立 round-3 独立判据；核验 60 文件与 candidate manifest。 |
| 2026-10-19 | 审查 API/query、SourcePanel Unicode 转换和 App navigation epoch/selection 调用链；全新构建 analyzer。 |
| 2026-10-19 | 执行完整 `verify_m1.sh`：110 backend、27 Vitest、4 Chromium 均通过。 |
| 2026-10-19 | 设计并运行真实 route-continue 时序变体；三次审核 harness 自身错误保留并修正，最终 call-edge/index-switch 反例 PASS。 |
| 2026-10-19 | 最终重核清单和候选文件一致；写入报告，未改候选或 Git 历史，未 commit/push/merge/release。 |
