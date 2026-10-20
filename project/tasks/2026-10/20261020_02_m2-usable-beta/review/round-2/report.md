# CodeWeave M2-A 独立实施审核第 2 轮报告（报告收口）

- 文档状态：FINAL
- 审核对象：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/review-2/candidate`
- 候选清单：`../candidate-manifest.json`，84 个文件，SHA-256 `40328a84bf1e27948e17d1916ebfd3489a2bc3c4fadadc4560e889703c4a7c95`
- 裁决：**ACCEPT**（仅限本报告实际验证的 M2-A 范围；不是对 M2-B/缓存复用/未来版本的结论）

## 0. 结论摘要

本报告是原独立审核会话 `06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6` 的报告收口续办，不是新候选、不是新审核轮。上一段受监管调度实际运行于 2026-10-20 14:10:01–14:40:02 UTC（`launch.json`、`process-result.json`），在 1800 秒上限被终止，父进程退出 124，**没有产生原生最终裁决，也没有 report/result**。因此超时、脚本通过、开发者自测通过均未被本报告当作 ACCEPT 的依据；完整原始流仍保存在 `review-2/` 下。本轮在同一会话中以新的独立工作副本完成证据收口。

独立证据表明 P1、P2、P3 三个旧问题均已在当前候选中纠正并通过针对性反例；独立重建的全 gate 通过 136 个后端测试、fixture 1、前端 38、真实 Chromium 7+2、零 skip；M2-A 必需用例 01–20 与 22 在本轮证据下为 PASS，21 与 B 缓存复用按用户明确要求为 OUT_OF_SCOPE。未发现必须阻断的安全、身份、快照、删除或输出错误。两个必须明确披露的非阻塞限制是：

- **N1（观察者 TU 保守过报）**：`definition_context_changed` 的输入是符号所有观察 TU 的正读集并集，不是“定义所在 TU 自己的读集”。因此某个符号的定义 TU 不读头文件，但另一个观察/调用 TU 读了头文件时，该符号仍可能收到 context 事件。独立 V2 已复现：`audit_remote_value` 定义在 `third.cpp`，`third.cpp` 不读 `settings.hpp`，但 `main.cpp` 读，事件仍出现在该符号上；`changed_inputs` 只列真实读取的 `settings.hpp`，没有虚构未读路径。 envelope/README/API 明确把此标为 observer-TU 级保守近似和“possible input-context change”。这是精度限制，不是本报告发现的虚假读集条目。
- **N2（同文件外部常量边界）**：同一定义文件内的外部 `constexpr` 改变可以只产生 `file_text_changed`/source 变化，不产生该函数的 `definition_context_changed`。独立反例 `edge-constexpr.dI5Hgx` 已复现：`external_value: 1 -> 2`，`diff-symbols total_count=0`，`diff-files` 有一条 `main.cpp` 的 `file_text_changed`（before `9ed4c8...`，after `015a9a...`）。这是排除 definition/primary source buffer 以保持纯移行与 body 编辑不产生符号 context 事件的直接结果，README、`docs/http-api.md` 和 comparison envelope 均已明确写出同 buffer 外部常量可能只在 file/source 层可见，且无事件不证明行为等价。它不隐藏文件级变化，也不是“未变更”的虚假声明；在 M2-A 当前合同下按**非阻塞限制**记录，不将它伪装成已检测。
- 另有若干低风险/尚未全量重放事项列于第 7 节，包括旧 84 文件矩阵未逐项重新构造、UI 理论上的 POST→terminal 竞态未被观察到、单裸 CR 行号边缘未单独构造，以及文档中一处 `at most8` 排版笔误。这些均未构成本轮必需合同的阻塞证据。

## 1. 身份、授权、只读边界与时间线

| 项目 | 实际值 |
|---|---|
| 会话 UUID | `06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6` |
| 实际运行模型 | `deepseek-flash[1m]` |
| 服务返回模型 | `deepseek-flash`（从原始 `stdout.jsonl` 的 assistant 记录核对） |
| effort | `max` |
| permission mode | `auto` |
| 审核日期 | 2026-10-20 |
| 本报告写入时刻 | 2026-10-20T14:47:19Z（22:47:19 +0800） |
| 候选分支 | `feat/m2-usable-beta` |
| 基线 HEAD | `95620d8da6afb8470d78400468fc4eee120147f2` |

身份不是“Opus”。`review-2/launch.json` 记录 `model_requested` 为 `deepseek-flash[1m]`、effort `max`、permission `auto`；原始流同时出现请求名 `deepseek-flash[1m]` 与服务实际返回名 `deepseek-flash`，本报告按此如实记录，不把两者混写。

**数据授权与传输**：用户已明确授权将本轮 84 个候选文件及必要审核材料发送至 `api.deepseek.com`，用于本限定的审核/修复复核循环。本报告因此不声称“未发送任何数据”。除该授权服务外，本轮没有把候选或真实私有项目/凭据/敏感材料上传到其他外部服务；安全负向测试只使用本会话自造的假私有哨兵。报告与结果文件仅写入审核目录，临时 fixture、数据库、构建和浏览器证据只在 `/tmp/cwaudit-review2` 及 `/tmp/codeweave-m2-acceptance-yZE9QA`。

**只读边界**：原始 `review-2/candidate`、`candidate-manifest*`、`changes-from-review-1.json`、旧 `round-5/audit/{report.md,result.json}`、DevFlower 的 `review/round-1`、以及原始生产源码均未修改；没有 commit/push/merge/rebase/reset/clean/stash/tag/release；没有触碰父 Agent 的 8000 端口服务；没有写入任何 DevFlower 文件。审计输出目录原本不存在，本报告首次创建；这正是本报告唯一新增的正式输出目录。审计过程中未在规范副本中生成 `__pycache__`，所有 Python 运行使用 `PYTHONDONTWRITEBYTECODE=1`；工作副本后来出现的构建/node_modules 只在 `/tmp`，不作为规范副本的一部分。

**上一段超时记录**：

- `review-2/launch.json`：`started=2026-10-20T14:10:01.569001+00:00`，PID 1025957。
- `review-2/process-result.json`：`exit_code=124`，`ended=2026-10-20T14:40:02.134045+00:00`。
- `review-2/report-completion/launch.json`：同一会话的续办入口，`started=2026-10-20T14:41:35.485333+00:00`，PID 1173235。
- 14:40 前的完整 stdout/stderr 与 launch/process-result 保留在 `review-2/`；本报告不把该次未完成运行计作一个已裁决轮次，也不把其日志中的任何脚本成功替代最终裁决。

## 2. 候选完整性、变更面和首末 84 文件校验

### 2.1 清单身份

| 项目 | 实测 |
|---|---|
| `candidate-manifest.json` 字节数 | 14,917 |
| 清单原始 SHA-256 | `40328a84bf1e27948e17d1916ebfd3489a2bc3c4fadadc4560e889703c4a7c95` |
| `candidate-manifest.sha256` SHA-256 | `31d63913e2de21a098ead1f085d4828cc0c9444d5a878c6745c469ee533aa16f` |
| `sha256sum -c candidate-manifest.sha256` | `candidate-manifest.json: OK`，exit 0 |
| 期望/实际文件数 | 84 / 84 |
| 期望总字节 | 502,305 |
| 缺失/哈希不符/mode 不符/额外文件 | 0 / 0 / 0 / 0 |
| `changes-from-review-1.json` SHA-256 | `78e252d0c4401d560bb68c86a22010165dd48ce794fbce0576b7a69ba7bde81c` |
| `deleted` | `[]` |

清单中的 Git mode 按可执行位核对为 `100644`/`100755`；规范副本文件系统呈现的 `0444`/`0555` 只是发布只读权限，不是 mode mismatch。没有对规范副本执行 `chmod`，也没有在其内生成导入缓存。

`changes-from-review-1.json` 声明的变更文件恰好是 10 个，与独立字节比较一致：

1. `README.md`
2. `backend/codeweave/app.py`
3. `backend/codeweave/diff.py`
4. `backend/codeweave/index.py`
5. `backend/tests/test_workspace.py`
6. `docs/http-api.md`
7. `frontend/e2e-m2/workspace.spec.ts`
8. `frontend/src/App.tsx`
9. `frontend/src/WorkspacePanel.tsx`
10. `frontend/src/api.ts`

旧候选 `round-5/candidate` 与本候选逐字节比较：84 个同名文件中 74 个完全相同、10 个变化；旧候选额外只有一个此前遗留的 `backend/codeweave/__pycache__`，当前规范候选不含它。C++ analyzer、`schema.py`、`workspace.py`、`snapshot.py`、`git_snapshot.py`、`cli.py` 和 `scripts/verify_m2.sh` 均未变化。重点未变哈希：

- `analyzer/main.cpp`：`e2c71ba0488c3e6bff1052ca99d9a81e675b5c2238100abd31cfd19a09e41507`
- `backend/codeweave/schema.py`：`5c0e3766d16755ddcd09e0afc368aebaa882d696d03f2bacc07895cb393156b3`
- `backend/codeweave/workspace.py`：`541ba1abf9407587ca5b80cdbc85042d2294dc66d40cf9d0e1feca8fb8f9b18b`
- `backend/codeweave/snapshot.py`：`c744ed4cf17f25161778c138c25ae93e37802c4414ebb12177aa410acd9da767`
- `backend/codeweave/git_snapshot.py`：`4df72a6662bd602d7046ee98d9127de82621820eeb1a80911d0c69985864d0a6`
- `scripts/verify_m2.sh`：`40bcad8832aaee5efae7a9d377521201147883e718e48865dd1cc819af303466`

### 2.2 首末校验（同一规范副本）

| 时点 | 证据 | 结果 |
|---|---|---|
| 开始时 | `/tmp/cwaudit-review2/logs/manifest-initial.json` | expected 84 / actual 84；missing `[]`、sha_mismatch `[]`、mode_mismatch `[]`、unexpected `[]`；total 502,305；manifest SHA `40328a84...` |
| 全部探测/UI 后 | `/tmp/cwaudit-review2/logs/verify_manifest.final.json` | 同上，84/84，三项空，total 502,305 |
| 另取全新 pristine copy 后 | `/tmp/cwaudit-review2/logs/verify_manifest.pristine-final.json` | 同上，84/84，三项空，total 502,305 |

后一次对 `/tmp/cwaudit-review2/work.sh54do` 做清单校验会看到 `frontend/node_modules`、`frontend/dist` 等构建产物，这是该工作副本用于构建的正常结果，不是候选新增文件；因此候选完整性以规范副本的三次校验和 pristine copy 校验为准，不把工作副本的 extra 计数当候选缺陷。规范副本最后仍为 `dr-xr-xr-x silver:silver`，无写入。

### 2.3 旧正式结论原样保留

- `m2-usable-beta-20261020/round-5/audit/report.md`：SHA `4a13838edc3fd834453a18a129ffdd6592fb4ff476f44af4711dd17061046079`。
- `round-5/audit/result.json`：SHA `aac2e391dbd61b773b9ae9a93955224c32c2fea897764e474fd3698009cc70db`，verdict `NEEDS CORRECTION`，manifest `ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb`。
- DevFlower `20261020_02_m2-usable-beta/review/round-1/{report.md,result.json,candidate-manifest.json}` 哈希与旧原件一致（`4a13...`、`aac2...`、`ae00...`），归档未被覆盖。

旧候选的 `ae00...` 结论未被本条新候选继承或改写；本报告只对 `40328a84...` 负责。旧 `round-5` 的 05/15 FAIL 仅作为历史背景，不作为当前证据；当前 05/15 由 V6/V8/V9 和当前 gate 重新验证。

## 3. 独立构建、全 gate 和真实浏览器结果

### 3.1 环境与重建

- Python：`/home/workspace/CodeWeave_dev/.venv/bin/python`，3.12.3。
- LLVM 18 前缀：`/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18`；资源目录 `lib/clang/18`。
- Node：v22.23.3；npm 9.2.0。
- `CODEWEAVE_BUILD_PARENT=/tmp`；`.venv`、toolchain 和规范候选只读。
- 独立工作副本：`/tmp/cwaudit-review2/work.sh54do`（路径保存在 `logs/workdir.txt`），由 `cp -a candidate/.` 后只对副本 `chmod -R u+w` 创建；未链接生产 `node_modules`。

在 work copy 中以后台任务 `biuw21fjb` 执行仓库入口 `bash scripts/verify_m2.sh`（`PYTHON` 指向 `.venv/bin/python`，`CODEWEAVE_BUILD_PARENT=/tmp`），任务退出码 0，完整日志 `/tmp/cwaudit-review2/logs/verify_m2.log`（SHA `43c2fe1bcaa271709ac3c16cbbb70ae462818f600ef94fd9d050b565f31fcedb`，119 行/6,312 字节），证据根 `/tmp/codeweave-m2-acceptance-yZE9QA`。最后一行：`PASS: complete M0/M1/M2-A gate. Evidence retained: /tmp/codeweave-m2-acceptance-yZE9QA`。

### 3.2 重建 analyzer

脚本从当前 `analyzer/main.cpp` 重新干净构建，不使用旧二进制：

- `analyzer/main.cpp` SHA：`e2c71ba0488c3e6bff1052ca99d9a81e675b5c2238100abd31cfd19a09e41507`
- 新构建 `analyzer/codeweave-analyzer` SHA：`b91b17afe37928da6f5f40374f20ee20e4f23f4d2505dfc417925e4e3c9b18b4`（47,131,096 字节，mtime 2026-10-20 22:11:24 +0800）
- CMake 正常完成；`main.cpp` 编译与链接均成功。

### 3.3 gate 各层实测

| 层 | 命令/范围 | 结果 |
|---|---|---|
| 后端 | `pytest`（当前候选测试，重建 analyzer） | **136 passed, 1 warning in 117.65s**；exit 0 |
| JUnit | `/tmp/codeweave-m2-acceptance-yZE9QA/backend.xml` | testsuite tests 136、errors 0、failures 0、skipped 0、time 117.646，timestamp `2026-10-20T22:11:24.525815+08:00` |
| fixture | `test_fixture_repo` | 1 test OK（0.017s） |
| bootstrap | 仓库边界检查 | `Bootstrap repository boundary checks passed (not a full secret scan).` |
| 前端安装/构建 | `npm ci`；`tsc --noEmit && vite build` | 124 packages；887 modules transformed；构建成功 |
| 前端单测 | vitest | 5 files / **38 tests** 通过（2.51s） |
| M1 真实 Chromium | Playwright | **7 passed (14.3s)**，零 skip |
| M2-A 真实 Chromium | Playwright | **2 passed (23.5s)**：usable loop 11.1s；context/source hashes/non-UTF8 7.3s |
| 总结果 | `verify_m2.sh` | exit 0；`PASS: complete M0/M1/M2-A gate` |

当前独立 gate 的 JUnit 中明确包含本轮纠正相关测试：`test_readset_constexpr_enum_context_with_hashes_and_real_cli_http`、`test_same_file_external_constant_stays_visible_as_file_delta`、`test_context_preview_byte_budget_keeps_full_readset_evidence`、`test_source_hash_windows_utf8_failure_and_integrity_cli_http`、`test_attempt_long_utf8_chunking_and_schema_rejection`。这些是当前候选测试的独立执行结果；开发者的自测日志 `m2-usable-beta-20261020/full-correction.log` 和证据目录只作为定位线索，不作为本报告的独立证明。

## 4. 旧 P1/P2/P3 逐项处置

### 4.1 P1：constexpr/enum/config-header 读集与 `definition_context_changed`

**实现核对**（`/tmp/cwaudit-review2/work.sh54do/backend/codeweave/diff.py`，共 293 行）：

- `POLICY_VERSION='m2a-diff-v2-readsets'`。
- `_side` 通过以下查询把每个 TU 的正读集和文件哈希连接起来：
  `SELECT u.source_file,u.path,f.sha256 FROM unit_files u JOIN files f ON f.index_id=u.index_id AND f.path=u.path WHERE u.index_id=?`；保存为 `reads[tu][path]=sha256`。
- `_symbol_inputs` 对所有观察 TU 取并集，并明确排除 `tu` 本身和 `symbol['definition_file']`；注释说明这些 buffer 有自己的范围/位置 delta，排除是为了不让移动函数或别的 body 编辑引发全文件上下文事件。
- `_context_changes` 生成三类变化：`profile`（profile ID before/after）、`input`（path+before_sha256+after_sha256）和仅在 ODR 不同且定义 buffer 哈希不同时的 `definition_buffer`。
- `_context_evidence` 取前 8 项，按规范 JSON（sort keys、compact、ASCII）字节数不超过 8,192 生成预览；输出 `changed_input_count`、`changed_inputs_truncated`、完整 `changed_inputs_sha256`、`changed_inputs_hash_format: json-sort-keys-compact-ascii-v1`，并固定 `odr_hint.authoritative: false`。
- 只有定义文件存在且 context 变化（或 ODR hint 变化）时进入 `definition_context_changed`；没有把 ODR 相等当作“无变化”的证明。
- envelope 额外输出 `context_scope`、`context_limitations` 和 `configuration_changed`，README 56–58 与 `docs/http-api.md` 129–142 明确说明 observer-TU 级粗读集、排除 definition/primary buffer、同 buffer 外部常量只在 file/source 层可见、无事件不等于行为等价。

**状态表**：

| 旧问题/子项 | 处置 | 独立证据 |
|---|---|---|
| 读集必须来自 `unit_files` + `files.sha256` | **CLOSED** | `diff.py` 查询与 join 实读；V2/V6/V7 的 header 输入均来自真实 `files.sha256`；`audit_unrelated_c` 未被列入 |
| `changed_inputs` 的 path/before/after | **CLOSED** | V2 `settings.hpp` `21fdfaa4... -> a9ec5a3a...`；V6 `macro_config.hpp` `e72d51ac... -> 54e30e9b...`；独立重算一致 |
| profile 变化 | **CLOSED** | 代码生成 `kind='profile'` 的 profile ID 对；当前 gate 的 `test_readset_constexpr_enum_context_with_hashes_and_real_cli_http` 覆盖 profile 分支并以精确 profile 身份输出；未用模糊文本替代 |
| ODR 非权威 | **CLOSED** | V2 `audit_macro_chain` ODR before/after 不等仍以 context 事件报告；事件 `odr_hint.authoritative=false`；无“ODR 相同即无变化”分支 |
| 预览 ≤8 项/8,192 字节，完整计数/集合哈希/格式声明 | **CLOSED** | V7 12 个长 UTF-8 header：count=12、preview 5 项、7,541 规范 JSON 字节、truncated=true、完整 12 项 canonical JSON 18,097 字节、集合 SHA `78e1fcf0ee1dd8adf732052c1b4753176d9e7e2500f09a3f8e0a2fe4158f481d` 独立重算一致；格式字符串精确 |
| literal-only、纯移行、重复/宏调用、lambda/local class 不回归 | **CLOSED** | V3 只产生 `definition_text_changed`，无 calls；V4/V5 只有 `location_changed` 与 `ambiguous_correspondence`，无新增/删除语义；当前 gate 136 项包含 lambda/repeated/macro 测试；V6 宏配置、V2 macro_chain 通过 |
| 不虚构未读 TU | **CLOSED（附 N1 精度限制）** | `changed_inputs` 仅含实际 `unit_files` 读取路径；V2 `audit_unrelated_c` 完全不出现；V2 `audit_remote_value` 的 `units` 是观察 TU 元数据，事件只列真实 `settings.hpp`；未见把不存在的路径写入 changed_inputs。观察者 TU 并集导致的符号级过报按 N1 披露 |
| README/API/envelope 边界说明 | **CLOSED** | README 56–58、`docs/http-api.md` 129–142、envelope 的 `context_scope`/`context_limitations` 均明确说明；未把同 buffer 边界隐藏为“已完整依赖分析” |

**P1 独立探针细节**：

- 自有六 TU 工程 `/tmp/cwaudit-review2/owned-fixture/project`；workspace `4c93bb95-db27-4adb-82cd-d4d489bb9b9b`；baseline V1 index `74ab04d5-daf0-4b6d-a7e4-774db87513ca`。
- **V2**（`settings.hpp` scale 2→4、enum 3→5）：新 index `e8e17d1f-0502-45ec-9886-48f08d2328f3`；`definition_context_changed` 8 个：`audit_remote_value`、`audit_target_alpha`、`audit_stable_literal`、`audit_uses_calls`、`audit_target_beta`、`audit_observer_a`、`audit_macro_chain`、`audit_observer_b`；`audit_unrelated_c` 不在其中；calls 0；files 1。`changed_inputs` 精确为 settings.hpp 的 before `21fdfaa4b2cd2182c82b580ab9e590fe36edae7e4d6a169311381dddf6ad2f71` / after `a9ec5a3a9987dd4fb81415d495f7e075a8aef992eb9840923ad6e860f96effac`；count 1，truncated false，format 正确；完整集合 SHA `770e889c319023dab4a8b97aa0f38a52a71bd278c7e2f1be27d1621e5b016ff4` 由独立 Python canonical JSON 重算一致。
- V2 中 `audit_macro_chain` 的 ODR before/after 不等，但 `definition_range` 的 buffer/range hash 相同，事件仍为 context，未被 ODR 短路；大多数其他符号 ODR 也相等，说明事件不是靠 ODR 差异伪造。
- **V2/N1 过报实例**：`audit_remote_value` 的 `units` 为 `calls.cpp, main.cpp, third.cpp`，定义 range 为 `third.cpp` begin 64/end 108、buffer `0ad9de89...`、range `496173...`、ODR 2144040647（两侧相等）；`third.cpp` 不读 `settings.hpp`，但 `main.cpp` 读。事件仍以实际 `settings.hpp` 为 changed_input。该行为是 `_symbol_inputs` observer-TU 并集的直接结果，不是 `changed_inputs` 列表造假；按 N1 记录。
- **V3**（`main.cpp` literal 7→8）：index `9abcc930-b268-4aec-b8f7-7ca75ef34396`；仅 `audit_stable_literal` 的 `definition_text_changed`；calls 0；files 1。
- **V4**（前置 `// moved lines only` 两空行）：index `2aad7122-13a3-4d88-9d63-1d993056ec5a`；4 个 `location_changed`（`observer_a`, `stable_literal`, `macro_chain`, `uses_calls`）；1 个 `ambiguous_correspondence`；无新增/删除语义。
- **V5**（移动 `audit_stable_literal` 到末尾）：index `da22c9a2-f14d-4f28-a786-1b9cd1b87f93`；3 个 `location_changed`（`macro_chain` 12→11、`stable_literal` 10→15、`uses_calls` 14→13）；`observer_a` 不变；1 个 `ambiguous_correspondence`；独立比较调用关系多重集相等。
- **V6**（`macro_config.hpp` 4→9）：index `93d1521c-47da-4651-85f7-f99732ec4f71`；7 个 context 事件；changed_inputs 精确为 macro_config before `e72d51ac632ea331a1b166eec5025c34e40011eb452af48d818a523b2052350e` / after `54e30e9ba93d8a2e102ae80295b88744bb8d0462f3176e36437fd08613b88494`；count 1；calls 0；files 1；`configuration_changed=false`；definition range 不变；独立重算哈希一致。
- **V7**（12 个长 UTF-8 header，`inline constexpr int audited_input_0..11 = 2`）：第一次把变量名改成超长中文导致 12 个未声明标识符，refresh 正确失败并保留旧 index（request `f00e2142-f883-427e-994b-57d6270dc54e`）；第二次复用 token `v7many` 被产品按 idempotency 返回同一失败 request，未发布；这是审计工作流错误，不是产品缺陷。使用新 token `v7many2` 后 index `8bc23c08-d801-427a-9380-e29d6772ed60`，6 个 TU，generation 7。V6→V7 的 `audit_many_reader` context 事件：count 12、preview 5/7,541 字节、truncated true、完整集合 SHA `78e1fcf0ee1dd8adf732052c1b4753176d9e7e2500f09a3f8e0a2fe4158f481d` 独立重算；page 8,141 UTF-8 / 11,291 ASCII 字节，低于 262,144；calls 空；files 12 条 `file_text_changed`。
- **同文件宏边界** `/tmp/cwaudit-review2/edge.wFyIVk`：`#define LOCAL_VALUE 1`→`2` 产生 `audit_same_file_macro` 的 `definition_context_changed`，changed_inputs 恰为 `kind=definition_buffer`、path `main.cpp`、before `4fee...`/after `8eeb...`，ODR 1668701082→3440139956；`audit_unaffected` 不报。这说明同文件宏可被精确定位，但也说明同文件非宏常量走的是不同路径。
- **同文件 constexpr 反例** `/tmp/cwaudit-review2/edge-constexpr.dI5Hgx`：`constexpr int external_value = 1 -> 2`；旧 index `72f9cb54-e0ed-49b9-82b6-daf6de740eab`，新 index `6df670f1-1cd4-41f2-9faf-6e6fc53fc371`，comparison `dce9f1424edda089252b601e085cadaffb073b5800efa2aca9969d53c1067c99`；`diff-symbols total_count=0`，`diff-files` 仅 `main.cpp` `file_text_changed` before `9ed4c8d98efc67e52289d5da2307346fe75beaa300a0c665950ee2ec01abedb1` / after `015a9aa8ffae057092716ab3a05dc1c8a5e07207bc404e55c49334eafbdd7691`；`configuration_changed=false`。该反例即 N2，未被隐藏。

**P1 总状态：CLOSED**。旧“头文件读集不存在/无法解释输入/ODR 冒充语义/预算丢失完整证据”的问题已由实现、V2/V6/V7 和当前 gate 重新证实关闭；N1/N2 是必须披露的精度边界，不构成本轮必需合同的阻塞失败。

### 4.2 P2：严格 UTF-8、无效输入显式错误、原始字节保留

**实现核对**（`backend/codeweave/index.py`）：source 分支先校验行号、最多 200 行，按行取原始 `bytes`，用存储的 `sha256` 校验 buffer；不能用 `content is None` 冒充已注册；非法 UTF-8 时抛 `IndexError('source_not_utf8', ...)`，不返回替换字符。响应包含 `encoding='utf-8'`、`sha256`、`buffer_sha256`、`range_sha256`、`begin`、`end`。`source_diff` 复用同一 `source` 查询；任一窗口解码失败会返回显式错误，unit diff 不产生混合文本。`rg` 检查：源码中没有 `errors="replace"`；`index.py:399` 仅对 status 字段预览使用 `errors="ignore"`，与 source/source-diff 窗口无关。`app.py` 将 `source_not_utf8` 映射为 HTTP 422，CLI `_fail` 输出单个 JSON 到 stderr 并 exit 2。

**状态表**：

| 子项 | 处置 | 证据 |
|---|---|---|
| 不再 `errors="replace"`，无效 UTF-8 显式 `source_not_utf8` | **CLOSED** | `rg` 全后端/前端/test/analyzer 未发现 replace；V9 行 2/1–2/1–3：CLI stdout 空、stderr 单个 JSON `source_not_utf8`、exit 2；HTTP 422；无 U+FFFD |
| 旧 index 原始字节保留 | **CLOSED** | V8 index `740f86d8...` 在 V9 后仍返回原始 87 字节与 SHA `e3c3...`；V9 新 index 不覆盖旧行 |
| 合法历史窗口、非法字节之外的合法窗口可读 | **CLOSED** | V9 行 1（begin 0/end 22，range `d28c9bc2...`）和行 3（begin 46/end 82，range `9594fe9f...`）可读；V8 行 1/2/3 全部可读且独立哈希一致 |
| source-diff 窗口失败显式错误、绝不混入替换文本 | **CLOSED** | V8→V9 合法行 3：exit 0，左右 range 均 `9594fe9f...`，left buffer `e3c3...`、right buffer `792908...`，diff 空，`windowed=true`；非法行 2：exit 2，单 JSON `source_not_utf8`，无部分输出 |
| 内容/CRLF/Unicode/哈希可独立重算 | **CLOSED** | V8 原始 bytes `b'// 中文注释 CRLF\r\n// emoji 😀 combining é\r\nint audit_unicode() { return 41; }\r\n'`，87 字节 SHA `e3c3b4b1750736daaa4aaf8404cfc4af00a884155674348aa7afc78482130016`；`splitlines(keepends=True)` 长度 `[22,29,36]`；三窗口 begin/end 0/22、22/51、51/87 与独立计算一致；窗口 SHA 分别为 `1bb271...`、`ebad16...`、`9594fe...`，与整文件 SHA 明确区分 |
| HTTP 与 CLI 语义一致 | **CLOSED** | 端口 18432 对 live V9 state：合法窗口 200、旧 index 200 原始 hash、非法窗口 422、合法 source-diff 200、非法 source-diff 422；日志 `/tmp/cwaudit-review2/owned-probe/http-live.log` |

**P2 总状态：CLOSED**。V8/V9 的旧/新 index 同时存在仍按各自字节读取，且没有任何替换文本混入。

### 4.3 P3：整文件/窗口哈希、原始偏移、完整性错误

**实现核对**：source 响应把 `sha256` 和 `buffer_sha256` 设为整文件存储哈希，`range_sha256` 为窗口原始 bytes 哈希；`begin` 是前 `start_line-1` 个 raw `splitlines` 字节长度之和，`end=begin+len(content)`；`encoding='utf-8'`。source 查询在读取后独立计算 buffer SHA 与 `files.sha256` 比较，不匹配即 `source_integrity_error`；打开连接为只读 URI，查询不会修复/重写数据库。`app.py` 将 `source_integrity_error` 映射 503；CLI exit 2。

**状态表**：

| 子项 | 处置 | 证据 |
|---|---|---|
| 整文件 `sha256`/`buffer_sha256` 与窗口 `range_sha256` 区分 | **CLOSED** | V8 整文件 `e3c3...` 与行 1/2/3 range 不同；V9 整文件 `792908...`；V8 全窗口 1–3 的 range 等于整文件 hash，单独窗口不等 |
| raw byte `begin`/`end` 与 `encoding=utf-8` | **CLOSED** | V8 begin/end 0/22、22/51、51/87；每个窗口独立 content bytes 重算；无字符偏移混用 |
| 内容/CRLF/Unicode/哈希独立可重算 | **CLOSED** | 见 P2 表；窗口内容 bytes 与 API 返回 content 完全一致，未归一化 CRLF |
| SQLite content/hash mismatch → `source_integrity_error`，HTTP 503/CLI 2 | **CLOSED** | 用 SQLite backup API 复制 state 到 `owned-probe/integrity.sqlite3`（10,612,736 字节，SHA `f4abe325...`）；将 index `509d4120...`/`third.cpp` 的 109 字节 content 中 `audit_unrelated_c` 替换为等长 `audit_unrelated_X`，保留原 stored SHA `0ad9de89...`；CLI source 第三文件 exit 2、stdout 空、单 JSON `source_integrity_error`；HTTP 503；source-diff 同样 exit 2/503 |
| 查询不修复/重写旧 DB，其他文件/旧 index 仍可读 | **CLOSED** | 损坏前后 DB SHA 与 row stored SHA 不变；无 journal 残留；旧 V8 index 仍返回 `0ad9de89...`；同损坏 index 的 `second.cpp` 仍返回 `eb046b...`；说明损坏被定位且不扩散、不自动修复 |
| 损坏查询不通过磁盘当前文件“修复” | **CLOSED** | 未触发重写；错误路径直接 fail-closed；只读连接打开 state 副本 |

**P3 总状态：CLOSED**。

## 5. UI 独立验证（真实浏览器）

自有 UI fixture `/tmp/cwaudit-review2/ui-fixture`（从自有工程复制并重写绝对路径，fresh state），workspace `d368b40c-97db-4e01-aa74-d1b648017061`，generation 3，latest index `5fcee629-56d9-4f1a-afdc-19fa105058fe`。索引身份：

- A baseline：`5df2a422-4e5e-42fb-89b7-2ee8086b78c6`，attempt `a5794c7c-77c3-4973-a4f9-11ac7c6f8a8b`，snapshot `f4536d...`，settings 4/5。
- B：`3647bd53-c854-4bf9-9db7-e097ba8ad1c1`，attempt `30bd3cdf-d762-4231-8b91-e43b8daddbb4`，snapshot `d21a3ec2...`，settings 6/7。
- C：`5fcee629-56d9-4f1a-afdc-19fa105058fe`，attempt `a9fa0099-7e95-4819-aef2-4cd43a545bcc`，同 snapshot。

真实服务端口 18434，使用 work copy 后端和已构建前端，启用 workspace refresh；服务日志 `/tmp/cwaudit-review2/ui-fixture/server.log`（PID 1114667，测试后已停止，未触碰 8000 端口）。Playwright 配置 baseURL `http://127.0.0.1:18434`，测试文件 `/tmp/cwaudit-review2/ui-audit/ui-audit.spec.ts`，node_modules 仅以 symlink 复用审计环境。

最终运行 `1 passed (8.7s)`，`PLAYWRIGHT_RC=0`，日志 `run3.log` 343 字节 SHA `c71cb0d6afa8bbe0b5b38b57657810ad0290f0163119f87d799f813bf1cbe716`；截图 `ui-audit.png` 149,971 字节 SHA `ceedfb5df711fbbe08cf252327ac37661735763b1501ccd47c89672d85607d60`。测试直接证明了：

1. 实际等待真实 B published（request ID 匹配），比较栏显示真实 left/right 版本对；不是 mock 的“发布”。
2. 选择 context 事件后，`changed_inputs` 精确为 `[{kind:'input', path:settings, before_sha256: originalHash, after_sha256: changedHash}]`；`changed_input_count` 正确；`odr_hint.authoritative=false`；独立递归 `sort_keys` canonical JSON 计算与产品 `changed_inputs_sha256` 一致。
3. source 详情显示整文件/窗口 `buffer_sha256`、`range_sha256`、`begin`/`end`；Monaco 文本为旧/新真实内容，不是替换字符。
4. 切换到基线 snapshot 后，历史搜索 `audit_observer_a` 与 source 仍可读，hash 对应 A 的快照；历史图谱/源代码均保留。
5. gating 测试对真实 `POST /api/workspace/refresh` 延迟 2,500ms，刷新未完成期间比较快捷键保持 disabled，C published 后启用并选择 B/C；测试观察期间无 page error。
6. 真实 published pair 的身份字段（index id、attempt id、snapshot、request id）与后端数据一致。

**UI 历史 harness 错误（如实保留）**：

- 第 1 次运行在哈希断言处失败：审计测试预期 `3aa119d4...`，产品返回 `7c497efe...`。原因不是产品，而是审计 oracle 只按 path 排序、没有递归 sort keys；独立 Python 用 `json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=True)` 重算，产品 `7c497efe...` 与文档格式一致（252 字节）。修正测试后继续。
- 第 2 次运行因 Python 字符串替换没有匹配实际 U+FFFF 字符而失败；改用行切片插入递归 canonicalizer 后通过。两次失败测试均已保留在 `/tmp/cwaudit-review2/ui-audit/` 的运行日志中，未隐藏。
- fixture 在两次失败后重置（状态/工程重拷、compile_commands 重写、baseline refresh、服务重启）；这属于审计 fixture 管理，不是产品行为。

**理论残留（非阻塞）**：`WorkspacePanel.tsx` 的 `post()` 只更新 `last_attempt`，`available` 要等后续轮询；当前刷新 POST 实际返回非终态，测试中 disabled 全程成立。若未来某实现让 POST 直接返回已发布终态，可能在极短窗口内继续显示旧 pair；本轮未观察到，也未将其升级为必需合同失败。另，版本下拉在 busy 时未禁用，但比较快捷键禁用，实际 UI 测试未出现用未完成刷新的版本比较。

## 6. M2-A 必需合同逐项判定

判定约定：PASS 表示本报告有独立执行证据或对未变更代码路径的当前 gate/字节核对足以支持，且不存在未解释的必需失败；21 和 B 缓存复用按用户指令不在本轮范围。这里不把旧 `round-5` 的结论机械继承；当前候选测试已在上述独立 gate 中实际运行。

| 编号 | 结果 | 本报告依据 |
|---|---|---|
| 01 字面量编辑 | **PASS** | V3：仅 `definition_text_changed`；无 phantom call；旧 index source bytes 保留（V8/V9 反向验证） |
| 02 唯一 return alpha→beta | **PASS** | 当前 gate 的 M2 usable loop 与 `test_workspace.py` 全过；relation key 无位置、唯一 token/AST 证据；无重复/歧义时 delta 为 confirmed |
| 03 prepend/move | **PASS** | V4/V5：USR、定义 bytes、调用关系多重集相等，仅 location_changed/ambiguous correspondence；无新增/删除语义 |
| 04 共享头 a/b 不涉及 c | **PASS** | V2：`audit_unrelated_c` 不被 context 报告；有真实读集的 a/b 消费者被报告；当前 gate 通过 |
| 05 macro-only 配置/-D | **PASS** | V6：7 个 context 事件、macro_config 精确 before/after、`configuration_changed=false`；README/API 说明 input 原因；当前 `test_readset...` 通过 |
| 06 inline/template 两 TU | **PASS** | 当前 136 后端测试 + 9 Chromium 全过；analyzer `main.cpp` 未变且新 analyzer 重新构建；相关 symbols/definition identity 测试无失败 |
| 07 add/delete/rename TU、stale ccdb | **PASS** | 当前 gate 的 scope/out_of_scope/physical deletion 测试通过；旧 index/current index 保留；未变 workspace/snapshot 逻辑 |
| 08 command/cwd/resource/config/duplicate/incompatible | **PASS** | 当前 136 后端 + M1/M2 Chromium 全过；workspace/profile/snapshot 代码字节未变；JUnit 无 skip/failure |
| 09 Git HEAD + staged/unstaged/untracked/deletion provenance | **PASS** | 当前 gate 的 Git/provenance 测试通过；`git_snapshot.py` 哈希未变；无 checkout/filter/hook 路径改动 |
| 10 capture barrier/seal mutation | **PASS** | 当前 gate 的 capture/seal 测试通过；`workspace.py`/`snapshot.py` 未变；未观察到 seal 绕过 |
| 11 单 TU 失败/缺头/warning | **PASS** | 当前 gate 的 failure/refresh/reload 测试通过；M2 e2e failure 路径保留旧历史；无把失败 TU 当删除 |
| 12 ENOSPC/constraint/cancel/kill before/after commit | **PASS** | 当前 gate 的 workspace/attempt 事务测试通过；未变 snapshot/schema；transactional publication 无失败 |
| 13 statics/overloads/shared header internal-external/reordered | **PASS** | 当前 gate 的 symbol/overload/static/linkage 测试通过；analyzer 未变；V4/V5 调用多重集独立核对 |
| 14 cycles/repeated/same-line/nested/lambda/virtual/pointer address | **PASS** | 当前 gate 的 diff/cycle/repeated/lambda 测试通过；V4/V5 重复调用仅 ambiguous，不臆造 target_changed |
| 15 中文/emoji/combining/CRLF/changed source/stale request | **PASS** | V8 原始 bytes、CRLF、中文、emoji、combining 和 87 字节/窗口哈希独立重算；V9 无效字节显式错误；旧 index 与合法窗口可读；当前 gate 全过 |
| 16 traversal/#line/symlink/FIFO/device/ccdb side-effect/hostile Git/std headers | **PASS** | 当前 136 后端测试与 M0/M1/M2 Chromium 全过；安全路径代码未修改；未执行导入项目构建/hook；标准头 frozen 机制未变 |
| 17 optional `__has_include`/earlier root header/equal-size-mtime | **PASS** | 当前 gate 的相关 include/profile 测试通过；analyzer 未变；decisions 的保守结构失效策略未变 |
| 18 schema3 migration/wrong schema/corruption/interrupted migration | **PASS** | 当前 gate 的 schema/migration/attempt 测试通过；`schema.py` 哈希未变；P3 损坏测试额外验证只读 fail-closed |
| 19 数百 snapshot/overlong UTF-8/pagination/budgets | **PASS** | V7 12 长 UTF-8 头的 7,541/8,192 预览和 11,291/262,144 页面预算；当前 gate 的 pagination/long UTF-8 测试通过 |
| 20 cross-origin/token/Host/idempotency/concurrency/restart | **PASS** | 当前 gate HTTP 安全测试；V7 复用 token 返回同失败 request（正确 idempotency）；UI 真实延迟 refresh gating；8000 未触碰 |
| 21 M2-B cache reuse/acceleration | **OUT_OF_SCOPE** | 用户明确排除；本报告不对缓存复用作 PASS/FAIL |
| 22 删除唯一 TU 但头中仍有声明 | **PASS** | 当前 `test_workspace.py` 的 case 22/scope 覆盖：`definition_removed`/`relation_out_of_scope`，不发明 definition；旧 index/current index 保留 |

**M2-A 强制集合结论**：01–20 和 22 全部 PASS；21 为用户指定的 OUT_OF_SCOPE；B 缓存复用的精确复用条款未作为本轮判据。未发现安全、身份、快照、删除、输出或 non-UTF8 行为的必需失败。

## 7. 限制、边界与未重放事项

1. **N1 observer-TU 过报（非阻塞）**：见 4.1。符号 `units` 是观察范围，`changed_inputs` 仅真实读集路径；`audit_remote_value` 的定义 TU 不读头但观察 TU 读头。它符合 README/API 的 observer-TU 保守语言，但不能被描述为“每个符号自己的精确读集”。若未来要求 per-definition 最小依赖，需要额外实现。
2. **N2 同文件外部常量（非阻塞，必须披露）**：见 4.1 的 `edge-constexpr` 反例。只报 file/source 变化，没有符号事件；文件级 before/after bytes 与 hash 完整，README/API/envelope 明示无事件不等于行为等价。排除 definition/primary buffer 是保持 case 03 纯移行/body 编辑稳定的必要选择；它不是把失败隐藏，而是 M2-A 明确的范围边界。
3. **旧 84 文件矩阵未逐项重新构造**：上一轮完整矩阵的证据仍保留，但本轮没有重新执行每一个历史 fixture。当前独立 full gate、当前 136 测试、9 Chromium，以及 V2–V9 自造反例覆盖了本轮更正影响的 P1/P2/P3 路径；未变更的 C++/schema/snapshot/workspace 代码通过字节哈希核对。因此本报告的 PASS 是“当前 gate + 变更面重点复测 + 未变路径审查”的 PASS，不是对每个旧 fixture 的重复证明。
4. **UI 理论 POST→terminal 竞态**：未观察到；当前 POST 返回非终态，真实延迟测试通过。作为低风险边界保留。
5. **单裸 CR 行号边缘**：已验证 CRLF、中文、emoji、combining、U+0085 假说（U+0085 不会造成 `bytes.splitlines` 边界），但未单独构造“仅有裸 CR 且与 Clang 行号交叉”的 fixture。它不是本轮已观测失败，不构成本轮核心不确定性；仍作为行窗口的未测边缘记录。
6. **status 字段 `errors="ignore"`**：只在 `index.py:399` 的状态字段预览，不影响 source/source-diff 窗口；P2 的替换字符禁令按 source 路径验证。
7. **文档排版**：`docs/http-api.md` 有 `at most8` 缺空格；不影响协议/字段/状态语义。
8. **安全边界/未使用材料**：没有使用 RMC、F11、参考实现、真实私有项目或凭据；负向测试只使用自造假私有哨兵；没有执行导入项目的构建/hook/脚本；没有额外外传。因用户授权，本轮审核材料确实可经 `api.deepseek.com` 传输，报告不作“未发送数据”的虚假声明。
9. **开发者自测**：`scripts/verify_m2.sh` 的开发者日志、`full-correction.log`、`/tmp/codeweave-m2-acceptance-chSR1a` 只作定位；本报告的 136/38/7/2 数字来自本会话的 `biuw21fjb` 和 `/tmp/codeweave-m2-acceptance-yZE9QA`。第一轮两个 testserver Host 错误与 UI timing 失败保留在历史上的开发者记录中，本轮未通过放宽 Host 或修改参考结果来“修复”。

## 8. 复现路径与证据索引

| 证据 | 路径 |
|---|---|
| 初始/最终/pristine 清单 | `/tmp/cwaudit-review2/logs/{manifest-initial,verify_manifest.final,verify_manifest.pristine-final}.json` |
| 独立全 gate | `/tmp/cwaudit-review2/logs/verify_m2.log`；`/tmp/codeweave-m2-acceptance-yZE9QA` |
| 后端 JUnit | `/tmp/codeweave-m2-acceptance-yZE9QA/backend.xml` |
| P1 V2–V7 | `/tmp/cwaudit-review2/owned-fixture/logs/{v2,v3,v4,v5,v6,v7}-diff-*.json` |
| 同文件宏反例 | `/tmp/cwaudit-review2/edge.wFyIVk/{diff-symbols,diff-files}.json` |
| 同文件 constexpr 反例 | `/tmp/cwaudit-review2/edge-constexpr.dI5Hgx/{diff-symbols,diff-files}.json` |
| P2 live CLI/HTTP | `/tmp/cwaudit-review2/owned-probe/http-live.log`；`/tmp/cwaudit-review2/owned-fixture/logs/` V8/V9 |
| P3 损坏 DB | `/tmp/cwaudit-review2/owned-probe/integrity.sqlite3`；`http-integrity.log` |
| UI 最终运行 | `/tmp/cwaudit-review2/ui-audit/run3.log`、`ui-audit.png`、`ui-audit.spec.ts` |
| UI 历史 harness 失败 | `/tmp/cwaudit-review2/ui-audit/` 中保留的 run 日志 |
| 旧正式报告/结果 | `/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/audit/{report.md,result.json}` |

关键 CLI 形式（均以实际 fixture DB/索引执行为准）：

- `codeweave query diff-symbols --database state/index.sqlite3 --left <index> --right <index>`
- `codeweave query diff-files ...`、`diff-calls ...`
- `codeweave query source --database ... --index-id ... --path ... --start-line ... --end-line ...`
- `codeweave query diff-source --left <old> --right <new> --left-path ... --right-path ... --left-start ... --right-start ... --lines ...`
- 无效 UTF-8 / 损坏 DB 的 source 与 diff-source 均以单个 JSON stderr 和 exit 2 结束。

## 9. 最终裁决

**ACCEPT**。

理由：当前候选的独立重建 gate 全层通过；P1/P2/P3 的旧缺陷均有当前实现和独立反例的关闭证据；M2-A 必需 01–20+22 全部 PASS；没有必须阻断的安全、身份、快照、删除或输出错误。两个真实精度边界 N1、N2 已在 README/API/envelope 明确披露，且 N2 仍保留完整文件级 before/after 证据、没有虚假“未变更”声明，因此不构成强制 ACCEPT 条件中的必需准确性失败。本裁决不宣称 M2-B、缓存复用或逐定义最小依赖已经实现；也不把上一段 1800 秒超时或任何脚本成功当作本次裁决。

报告结束。
