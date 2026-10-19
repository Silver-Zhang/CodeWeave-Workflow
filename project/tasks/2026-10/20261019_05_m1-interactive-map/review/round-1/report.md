# CodeWeave M1 Round-1 独立审核

## 1. 目标与范围

**裁决：NEEDS CORRECTION。** 本轮不能接受或建议提交/冻结当前 M1 候选；发现一项 M1 必需的 **P2** 源码定位正确性问题。

审核对象是固定完整候选，而非历史 M0 结论：

- 候选：`/home/workspace/CodeWeave_dev/m1-interactive-map-20261019/round-1/candidate`，M1 基线 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`，目标分支 `feat/m1-interactive-map`。
- 清单：58 文件，候选清单原始 SHA-256 `8243cbbc1b891dab6a437cc19acdb62c59e8971ee578d285d59daf1a87006ff4`。审核开始及结束均重新逐文件核验 byte size、SHA-256 与可执行 mode；两次均 58/58 一致、无错误。没有修改候选或其测试。
- 范围：M1 的 FastAPI 本地只读接口、与 M0/CLI 的同一事实内核、React/React Flow/Monaco 本地交互图、快照源码定位及安全/预算/错误边界。所有自主 fixture、SQLite、构建、node_modules、日志和 harness 在 `claude-artifacts/review/round-1/` 或临时目录；没有读取 RMC、reference、F11 或真实私有数据。

本审核先依据合同拟定 [`checklist.md`](checklist.md)，阅读候选源码、构造独立 HTTP/CLI/Chromium 检查，之后才接收 Unicode 定位反例材料。没有以 M0 ACCEPT、实施报告或测试数量替代本轮事实。

## 2. 做法与证据

### 独立环境与构建

- Python 3.12.3：`/home/workspace/CodeWeave_dev/.venv/bin/python`；CMake 3.28.3；GNU C++ 13.3；LLVM/Clang 18.1.3；Bubblewrap 0.9.0；Node 22.23.3/npm 9.2.0。
- 显式、已验证的 Clang resource dir：`/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18/lib/clang/18`（其 `include/stddef.h` 存在）。
- 从候选的 `analyzer/` 在审核目录全新构建：`builds/analyzer/codeweave-analyzer` SHA-256 `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；`main.cpp` SHA-256 `23ada772…a2842b`。
- 前端依赖在候选 `frontend/node_modules` 新装：`npm ci --no-audit --no-fund`；Node 22 下 typecheck、production build 和 Vitest 实际完成。

### 静态架构审查

- `backend/codeweave/app.py:16-116` 仅将受信启动数据库路径交给 `index.query()`；HTTP client 不提供 database 参数。`/api/search`、`symbol`、`calls`、`neighbors`、`source` 与 CLI 是同一 `query()` 内核。
- `backend/codeweave/index.py:463-578` 用 SQLite read-only 连接，显式分页、limit、source snapshot 注册检查、262144 serialized-byte 总预算，并将 neighbors 保持局部（direction limit 1..50）。虚调用保留 static declaration，函数指针 target 以 `unknown:<instance_id>` 表示而未伪造确定目标。
- `frontend/src/App.tsx:14-24,36-45,77-83` 以 index_id gate、epoch 和 AbortController 清理旧请求；`graph.ts:4-20` 以 USR/instance_id 去重，并限制 100 节点、150 edges、24 requests。图标签把 virtual 明示为 `static target`，unknown 节点明确未解析。
- 重大定位缺陷见 §3：`SourcePanel.tsx:15-17` 将 Clang UTF-8 byte column 直接作为 Monaco UTF-16 column。

### 实际独立验证

| 命令/验证 | 实际结果 |
|---|---|
| `cmake -S candidate/analyzer …` + `cmake --build …` | exit 0，新 analyzer 如上 |
| `PATH=<Node22> npm ci && npm run typecheck && npm run build && npm test -- --reporter=verbose` | exit 0；6/6 Vitest；production Vite build。Monaco lazy chunk gzip 694.53 kB，只有 Vite >500 kB warning，不是本轮阻塞项 |
| `CODEWEAVE_LLVM_PREFIX=… CODEWEAVE_RESOURCE_DIR=… PYTHON=… bash candidate/scripts/verify_m1.sh` | exit 0；后端 **103 passed**、0 failure/error/skip（1 条既有 Starlette 弃用 warning）；Python fixture 1/1；前端 6/6；Playwright 实际 Chromium 2/2 |
| `independent_api_check.py`（审核自有 fixture，公共 CLI index + TestClient HTTP） | exit 0，见 `independent-api-results.json`：status/search/symbol/calls/neighbors 各与 CLI 字节结构相等；两版 index snapshot 的 source 分离；virtual/unknown 与 API 相符；哨兵路径读取拒绝、跨源拒绝、DB SHA 未变 |
| 候选结束身份复核 | manifest 原始 SHA 与目标一致；58 文件均匹配 |

独立 API harness 的两次早期失败未计作产品失败或通过：第一次自身候选路径计算错误，第二次把 compile_commands **文件**而非目录传给产品。两者均修复为审核脚本参数/路径后，由我实际运行得到上表 PASS；`codex-executed-independent-api.log`/`codex-execution.json` 是 Codex 代执行的失败证据，不被表述为本审核实测或通过。

独立 Chromium snapshot harness 的若干早期失败同样不是产品结论：错误 import、Playwright strict locator、Monaco DOM 将空格显示为 NBSP 的文本断言、以及测试自身未等待受控搜索结果。它们说明该 harness 尚未形成独立 UI PASS，不能替代候选 `verify_m1.sh` 已实际执行的 Chromium 2/2；也不能被转述为产品缺陷。它们保留在 `independent-browser-check.log` 和任务输出中。

## 3. 决策记录

### P2-1：非 ASCII 调用点在 Monaco 的光标定位错误

- **位置：** `frontend/src/SourcePanel.tsx:15-17`；调用点列来自 `frontend/src/App.tsx:123,129` 的 `call.column_number`，随后原样传入 `editor.setPosition({ lineNumber: at, column })`。
- **触发：** 已保存 C++ 源码同一行、目标调用之前存在非 ASCII UTF-8 字符，特别是 BMP 多字节字符或 emoji/surrogate pair。例如：
  ```cpp
  void entry() { const char *s = u8"汉😀"; (void)s; target(); }
  ```
- **可复核事实：** 审核独立计算该前缀：UTF-8 byte column=54、UTF-16 column=50（命令输出一致）。附加材料在 `unicode-check/` 由真实公共 CLI + Clang/Bubblewrap 建索引、HTTP 读取 facts、真实 Chromium 运行候选生产页面获得：Clang call `column_number=54`，Monaco `getPosition().column=54`，预定义 UTF-16 预期=50；见 `unicode-check/oracle.json`、`facts.json`、`result.json` 与 `browser-process.json`。该材料不是我的实测，故作为可复核外部原始证据；其数值和候选代码路径与我独立静态审查/UTF-8 vs UTF-16 计算相符。
- **影响：** 图中边、call-site 按钮和标题仍诚实显示 Clang 的物理 UTF-8 byte column 54，但 Monaco 将 54 解释为 UTF-16 code-unit column，光标落在实际调用之后。M1 合同要求“点击调用关系可以在源码面板定位真实调用点”，因此多字节源码时该保证失效。不是事实污染或任意文件读取，但属于源码导航的必需正确性/可用性问题。
- **建议修复：** 保留 API/标题中 Clang byte column 原值；在 `SourcePanel` 或明确的展示转换层，对 `source.content` 的本地行按 UTF-8 byte offset 转换为 Monaco 1-based UTF-16 code-unit column，处理非 BMP surrogate pair、组合字符、非法/边界 byte offset并 clamp 到行合法范围。不要把 Clang facts 改为 UTF-16，也不要直接以 JS string index 代替 byte offset。
- **必要回归：** 真实 Clang + public CLI/HTTP + Chromium，至少覆盖 ASCII、`汉`、emoji、两者组合、调用在行尾、definition 与 call edge 两种定位；同时断言标题仍是事实列、Monaco `getPosition()` 是转换后的列、index_id/快照未变。

没有确认的 P0/P1。前端静态大 Monaco chunk、HTTP TestClient 的弃用 warning、简单网格布局均不构成本阶段合同失败；高级布局/大规模性能不属于本轮必过范围。

## 4. 结论与边界

**NEEDS CORRECTION。** 当前候选的 API、局部事实图、快照/身份隔离、错误与安全边界在已运行范围内有充分正向证据；但 P2-1 使非 ASCII 源码的必需“边/调用点 → 精确 Monaco 源码定位”失败。不得以 `ACCEPT WITH LIMITATIONS` 掩盖该必需缺口。

逐条合同判定：

- 同一 SQLite/CLI/HTTP query/index_id/facts：**PASS（已独立比对）**。
- 本机只读、JSON 错误、分页/预算、来源/host 边界：**PASS（已独立比对）**。
- 真实 C++ 索引、unknown/virtual/调用实例/环与局部预算：**PASS（候选全验收 + 源码/独立 HTTP 验证）**。
- React 真实 API 数据、去重、局部展开/收起、切换 index_id 清理、加载/空/错：**PASS（源码、Vitest、候选真实 Playwright；独立浏览器 harness未完成PASS）**。
- 点击节点/边精确源码位置和快照：**FAIL：P2-1 Unicode 列坐标错误；快照身份本身 PASS。**
- 全新构建和真实浏览器：**PASS（候选 verify_m1 实际执行）**；我的额外 browser harness仅用于补充，未独立完成成品 PASS。

修复后必须固定新候选、重跑受影响的真实 Chromium/Clang 反例、完整 M1 验收，并进行**新的完整候选独立审核**；不得只回复本报告或复用本轮结论。

## 5. 过程记录

| 时间 | 事件 |
|---|---|
| 2026-10-19 | 读取 M1 合同、固定本轮独立检查表，读取候选清单/源码；验证 58 文件身份和 manifest raw SHA。 |
| 2026-10-19 | 全新 CMake 构建 analyzer；Node22 全新依赖、typecheck/build/Vitest；运行完整 `verify_m1.sh`，含真实 Clang/Bubblewrap 和 Chromium。 |
| 2026-10-19 | 运行审核自有公共 CLI/HTTP 对照；保留并纠正审核脚本的路径/ccdb 目录错误，最终实际 PASS。 |
| 2026-10-19 | 编写额外 Chromium snapshot harness；其 import/strict locator/NBSP 文本/异步选择失败均为 harness 问题，未冒充产品 FAIL/PASS。 |
| 2026-10-19 | 在自主源码和运行判断后读取 Unicode 可复核材料；独立重算 byte/UTF-16 列差，确认 `SourcePanel` 原样传列导致 P2-1。 |
| 2026-10-19 | 结束时重核候选 manifest 与 58 文件仍一致；未修改候选、旧任务或 Git 历史，未 commit/push/merge/release。 |
