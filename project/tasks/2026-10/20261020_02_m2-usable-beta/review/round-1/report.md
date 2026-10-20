# CodeWeave M2-A 可用版独立审核报告（round 5）

## 0. 裁决与审核身份

**裁决：NEEDS CORRECTION**

- 审核日期：2026-10-20
- 审核会话：`06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6`（原 CodeWeave 独立审核会话，round 5 分段续办）
- **实际模型：`deepseek-flash[1m]`（服务返回 `deepseek-flash`），effort=`max`，permission=`auto`。不是 Opus；本报告不冒称 Opus。**
- 审核对象：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/candidate`
- 候选清单：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/candidate-manifest.json`
- 清单 SHA-256：`ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb`
- 校验文件：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/candidate-manifest.sha256`（不是 `.json.sha256`）
- 声明 base：`95620d8da6afb8470d78400468fc4eee120147f2`；分支：`feat/m2-usable-beta`
- 文件数：84（含未提交/新增文件；清单项只有 `path`/`mode`/`sha256`，无 `bytes` 字段）
- 审核性质：仅审核；没有修改候选、生产源码、测试预期或 DevFlower；没有 commit/push/merge/rebase/reset/clean/stash/tag，也没有发布。

实际裁决依据是：必需合同 01–20/22 并未全部通过。case05 的读集/输入上下文 Diff 存在真实缺陷（P1），case15 的非 UTF-8 字节保真/源响应哈希子项也存在真实输出边界缺陷（P2/P3）。因此不能 ACCEPT，也不能用 LIMITATIONS 掩盖；但证据足以复现缺陷，故不是 BLOCKED。

## 1. 环境与工具链

- Python：`/home/workspace/CodeWeave_dev/.venv/bin/python`，Python 3.12
- LLVM/Clang：18.1.3；`CODEWEAVE_LLVM_PREFIX=/home/workspace/CodeWeave_dev/.toolchain/llvm-18/usr/lib/llvm-18`；resource dir：`lib/clang/18`
- Bubblewrap：0.9
- CMake：3.28
- Node 22：`/home/workspace/CodeWeave_dev/.toolchain/node22/node_modules/node/bin`
- Chromium：本机 ready
- 工具链与 `.venv` 均为只读使用
- 工作副本：`/tmp/cwaudit5/verifycand-JSnR6p`；构建/正式验收证据：`/tmp/cwaudit5/verifybuild/codeweave-m2-acceptance-HMhWlh`
- 所有自有输入、构建、state、HTTP/Chromium 服务均在 `/tmp/cwaudit5` 或 `/tmp/codeweave-context-probe-biayy7x0` 下；未使用用户 workspace 或 audit 目录作为 build parent/state。

## 2. 候选身份与首末核验

### 2.1 清单与原始仓库身份

- `git -C /home/workspace/CodeWeave_dev/CodeWeave rev-parse HEAD` 返回 `95620d8da6afb8470d78400468fc4eee120147f2`，与声明 base 相同；当前分支为 `feat/m2-usable-beta`。
- 候选目录本身没有 `.git`（`candidate/.git` 不存在），所以本报告所说的 Git mode 是对候选文件权限位按 manifest 规则核验：可执行位为 `100755`，否则 `100644`；同时核验字节 SHA-256。
- `sha256sum -c candidate-manifest.sha256` 在 `round-5` 目录执行：`candidate-manifest.json: OK`，退出码 0。
- Python 核验脚本 `/tmp/cwaudit5/verify_manifest.py` 以 manifest 为真源，逐文件读取实际字节并计算 SHA-256，同时按可执行位判定 mode；首核验和报告前复核均为：
  - expected=84，actual=93
  - `missing=[]`
  - `sha_mismatch=[]`
  - `mode_mismatch=[]`
  - 84 个 manifest 文件字节与 mode 全部匹配；manifest 中 `total_expected_bytes=478142`
- actual 比 84 多出的 9 个文件全部是候选目录内 `backend/codeweave/__pycache__/*.cpython-312.pyc`。它们是审核过程导入候选模块时于 20:15:38 生成的，不在 manifest 中；本审核**没有删除**它们（删除会改变候选目录），在此披露为审核产生的非清单附加物。它们不改变 84 个受审文件的字节或 mode。
- 报告前可复核快照：`/tmp/cwaudit5/logs/final_manifest_pre_report.json` 与 `/tmp/cwaudit5/logs/final_manifest_prewrite.json`，字段相同；`rc=0`。
- 报告落盘后再次执行同一脚本，结果见本报告最后一节。

### 2.2 候选文件与工作副本

- `/tmp/cwaudit5/cand` 与 `/tmp/cwaudit5/verifycand-JSnR6p` 均由候选用只读方式复制；复制后源文件 SHA-256 与 84 项 manifest 一致。
- 正式验证使用的分析器：`/tmp/cwaudit5/verifybuild/codeweave-m2-acceptance-HMhWlh/analyzer/codeweave-analyzer`
  - SHA-256：`b91b17afe37928da6f5f40374f20ee20e4f23f4d2505dfc417925e4e3c9b18b4`
  - 与 round-2 独立新构建的分析器 SHA-256 相同；`analyzer/main.cpp` SHA-256 为 `e2c71ba0488c3e6bff1052ca99d9a81e675b5c2238100abd31cfd19a09e41507`。
- 没有用实现者自验代替本轮证据；实现者 README 只在初步判断后阅读，作为背景，不作为通过依据。

## 3. 独立预期与审核方法

独立预期来自以下只读规范，而不是实现者报告：

- `requirements.txt`：M2-A 的完整用户目标。
- `architecture.md`：§7/§8 的索引、封存、快照、Diff、source、安全与输出预算；尤其第 129 行的定义语义。
- `acceptance.md`：必需 01–20 + 22；21 和 B 专属复用/加速不属于 M2-A。
- `decisions.md`：protocol3 语义 USR、定义范围/哈希、独特调用配对；ODRHash 仅提示。
- `review/round-2/report.md`：读集只用于保守失效，positive read-set 不是完整依赖模型。

审核按 C/D/L/H/B 层执行：

- C：真实 Clang + Bubblewrap 分析器与真实 C/C++ 输入。
- D：SQLite schema 4、索引/快照/attempt 关系与 Diff 查询。
- L：独立公共 CLI 进程（非库内调用）。
- H：真实本地 HTTP 服务和真实安全负例。
- B：真实 Chromium 页面与真实索引。

Mock 只用于故障/时序控制；没有用 Mock 合成成功的文件、AST、Diff 或浏览器事实。

主要真实命令与退出码（详细原始日志均在 `/tmp/cwaudit5`）：

- 正式验收：`scripts/verify_m2.sh`（明确 `CODEWEAVE_BUILD_PARENT=/tmp/cwaudit5/verifybuild`）→ `VERIFY_EXIT=0`；日志 `/tmp/cwaudit5/logs/verify_m2.log`。
  - 后端：`132 passed, 1 warning in 101.13s`；JUnit `/tmp/cwaudit5/verifybuild/codeweave-m2-acceptance-HMhWlh/backend.xml` 为 `errors="0" failures="0" skipped="0" tests="132"`。
  - fixture：`test_fixture_repo.FixtureTest.test_two_commits_with_expected_delta ... ok`。
  - 前端：`Test Files 5 passed (5)`，`Tests 38 passed (38)`。
  - 真实 Chromium：M1 `7 passed (13.5s)`，M2 `1 passed (15.7s)`。
- 候选清单：`sha256sum -c candidate-manifest.sha256` → 退出 0；`verify_manifest.py` → 退出 0。
- 公共 CLI 示例（argv/退出/JSON 全记录）：`definition-context-probe.json` 中每条均为 `exit_code: 0`，包括 `workspace configure`、两次 `workspace refresh`、`query diff-symbols`、`query diff-calls`、`query diff-files`。
- 自建 case23 的 `query diff-*` 三条命令均退出 0；行为二进制 `behavior_old.bin`/`behavior_new.bin` 均退出 0，输出分别为 `leaf=4 root=5`、`leaf=18 root=19`。
- 真实 Chromium 独立用例：`chromium-case01.log`（1 passed）、`chromium-cases02-03.log`（1 passed）、`chromium-case15.log`（1 passed）、`chromium-case15-cursor.log`（1 passed）、`chromium-case09.log`（1 passed）、`chromium-case14-19.log`（2 passed）、`chromium-stale.log`（2 passed）。
- HTTP 安全/生命周期：`case20-security.json` 的 26 项负例/正例全部得到预期状态码；`case20-refresh.json`、`case20-busy.json`、`case20-restart.json` 为真实 worker 状态与重启结果。

## 4. 合同 01–20/22 逐项结论

状态只使用 PASS / FAIL / BLOCKED / 非本轮范围。每一项都附本轮真实证据摘要。

| 合同 | 状态 | 本轮证据与结论 |
|---|---|---|
| 01 | PASS | 真实 CLI 两次索引后只改函数 literal（7→9），Diff 只产生 `definition_text_changed`，调用关系没有伪变化；旧索引 source 仍返回原字节。Chromium `literal.spec.ts` 1 passed（`/tmp/cwaudit5/case01/logs/chromium-case01.log`）。 |
| 02 | PASS | 唯一 token/AST 证据下调用目标 alpha→beta：`d1-cal.json` 为 1 `relation_added`、1 `relation_removed`、1 `target_changed`；`d1-sym.json` 2 个定义文本变化。没有按行号/序号猜测。浏览器 `chromium-cases02-03.log` 1 passed。 |
| 03 | PASS | 仅移行：`d2-diff-symbols.json` 16 项全部 `location_changed`；`d2-diff-calls.json` 6 项 `site_location_changed`，语义关系增删均为 0；没有伪 target/关系变化。 |
| 04 | PASS | 共享头修改只影响实际消费者：`d3-diff-symbols.json` 只有 `shared_add` 的 1 个 `definition_text_changed`；其他 TU/未消费者没有伪变化；全量刷新重新分析，未复用旧 AST。 |
| 05 | **FAIL** | 宏头 `DEMO_SCALE 4→5` 时 `use_config` 确实产生 `definition_context_changed`（`d4-diff-symbols.json`），但事件只有 `confidence='input-context, not runtime behavior'`，**没有 exact changed inputs**。更强的自建 head/constexpr/enum 读集变更（case23ctx）定义字节、定义范围、ODR、profile 全部相同，Diff 的 symbols/calls 为 0，仅 header `file_text_changed`，完全漏掉消费者函数。详见 P1。 |
| 06 | PASS | 共享头/inline/template 跨 TU：`d6-sym.json` 9 项；两个 `shared_max` USR 均有定义范围，`units` 同时包含 alpha.cpp+beta.cpp；没有 first-TU-wins。template 专项 `r5-tmpl-*` 也通过。 |
| 07 | PASS | selected 新增/重命名/删除与 scope：`c07_*`、`r5-rename-*`、`r5-scope-*`；`c07_incompat.err` 为 `multiple_configurations`，`c07_stale.err` 为 `stale_compilation_database`，均拒绝而非猜测。`r5-scope-diff-symbols.json` 中 beta 在保留声明时是 `definition_removed` 且 `coverage_change='out_of_scope'`，不是 `symbol_removed`。 |
| 08 | PASS | 重复命令不放大：`c07_dup.out` unit_count=4；`c08_flag.out` unit_count=4；不同配置/冲突拒绝；`r5-rename` 的 `configuration_changed=true` 与 profile 变化可见。 |
| 09 | PASS | raw Git HEAD 与 workspace 索引分离：`state_head` 索引 `9e458f77...`，snapshot `39fd48b3...`，source_kind=workspace，base=`46e95ea3...`，represented=null；`state_head2` 索引 `d99e105f...`，snapshot `4bc2d07a...`，base/represented=`46e95ea3...`。Chromium case09 用 HEAD `d99e105f...` 渲染保存的 `return 1;`/`one()`；`test_missing_head_inputs_block_only_head_and_staged_saved_provenance`（`backend/tests/test_workspace.py:342`）证明缺历史生成输入只阻断 HEAD，不阻断 staged 保存证据。 |
| 10 | PASS | 封存后宿主修改：`mut_capture.err` 为 `workspace_changed_during_capture`，旧指针仍为 `85ef867f...`；正向 `mut_positive.json` 发布 `60e8648b...`；`tamper_refresh.err` 为 `sealed_input_changed`，篡改额外输入被拒绝；`mut_status_after_fail.json` 仍指向旧成功索引。c08/共享头用例均以同一 sealed 输入集分析。 |
| 11 | PASS | 语法错误/缺头：`analysis_failed`，不发布，旧指针 `e2d1417f...` 保持；warning 发布 `2214f36d...`，coverage=`units_complete`、warning count=1；driver 错误 `fail_driver*.json/.err` 被拒绝。 |
| 12 | PASS | 事务中断/取消：ENOSPC 后旧指针 `c720e078...` 的旧源仍可查（`enospc_old_src.json`）；约束失败旧指针保持；`cancel_enqueue.json` → `cancel_response.json` 为 `cancelling`，旧指针不变；SIGKILL 后 `open_recover.json` 显示 latest_successful_index 旧 `60e8648b...`，last attempt=`interrupted`，`result_index_id=null`，没有半索引。 |
| 13 | PASS | 同名 static/重载/跨 TU：`c13_diff_symbols.json` 6 项全为 `location_changed`；`shared_inline` 只有一个 USR；`shared_internal` 为 `@file=shared.hpp@tu=left/unit.cpp` 与右侧不同 USR；static helper 按 file/TU 区分；`c13_diff_calls.json` 出现 `ambiguous_correspondence`，保守不配对。 |
| 14 | PASS | cycle/重复调用/宏/lambda/虚函数/未知/取地址：`c14_diff_symbols.json` 14 项 `location_changed`；`c14_diff_calls.json` 5 个 `ambiguous_correspondence` + 6 个 `site_location_changed`，语义关系增删 0；没有把未知或重复上下文强行配对。Chromium `case14.spec.ts` 通过。 |
| 15 | **FAIL** | 指定正例（Chinese/emoji/combining、CRLF、旧索引 source、UTF-16 光标、双版本 stale 隔离）通过：`c15_source_a_final.json` 157 bytes SHA `d3b20c19...`，`c15_source_b_final.json` 161 bytes SHA `85eb8716...`，`c15_diff_files.json`/`c15_diff_symbols.json` 带两侧哈希；`chromium-case15*.log` 均通过。但额外真实字节负例 `/tmp/cwaudit5/case15bad/proj/bad.cpp`（61 bytes，SHA `15f2e9e0...`，含 `0xFF`）经 CLI 与 HTTP `/api/source` 均被 `errors="replace"` 成 U+FFFD，返回 63 bytes、SHA `99d4aec9...`，不是原索引字节；同时 source/source-diff 响应不带 SHA-256。合同原文未把“original indexed byte slices and hashes”限定为合法 UTF-8，故该子项 FAIL。详见 P2/P3。 |
| 16 | PASS | 安全负例：`fifo.err` 为 `unsupported_input ... nonregular input: escape_fifo`；`symlink.err` 为 `unsupported_snapshot_link ... project/dependency symlink`；`shadow.err`/`sentinel_src.err`/`hdr_source.err`/`hdr_diff.err` 为 `source_not_registered`；response file / `-D @file` 被 `unsafe_compilation_argument` 拒绝；`-fplugin`、`-Xclang`、`-MJ` 拒绝，退出 2，旧指针/status 保留。`status.json` 显示 diagnostics 0/0/0、coverage units_complete、input_count=162、frozen standard headers；正常 `<vector>`/`<cstddef>`/header methods 成功。Git execve trace 中 7 次 `/usr/bin/git` 均为 private stub `--git-dir ... -c core.fsmonitor=false` 的 `rev-parse`/`ls-tree`/`cat-file`/`ls-files`，无 `/bin/sh`/hook/filter 执行。`/tmp/cwaudit5/case16/outside/git_sentinel` 的 mtime 21:11:25 是审核者在产品 trace（20:13:55）之后自行运行 `git -C ... status --porcelain` 造成的；产品 trace 未触发 hook/filter，此归因如实披露，不声称哨兵未被审核者触碰。 |
| 17 | PASS | optional `__has_include`/搜索根/等大小 mtime 恢复内容编辑：`test_namespace_optional_header_and_equal_metadata`（`backend/tests/test_workspace.py:259`）与 `test_...` 真实运行；namespace 改变强制全失效，内容编辑触发读消费者重新分析，没有缓存旧目标。`optional` 证据文件与 c14/c15 配置一致。 |
| 18 | PASS | schema3 迁移：`migrate.out` 为 `{"database": .../migrated.sqlite3, "original_unchanged": true, "schema_version": 4}`；legacy 状态仍可读 schema3 索引 `8bed09a0...`、coverage units_complete；legacy Diff 明确拒绝；错误 schema/缺库/损坏库失败，未做原地自动升级。 |
| 19 | PASS | 分页/预算/长 UTF-8：Chromium case19 处理 260 个事件页和长 UTF-8 路径，2 tests 通过；`/api/source` 200 行/32768 bytes 预算、事件页 ≤262144、JSON 错误 `{error:{code,message}}` 无 traceback；长诊断/命令分块与 300 unit 预算测试在正式 suite 中通过。 |
| 20 | PASS | HTTP 安全与双版本：`case20-security.json` 26 项全部预期（Host/Origin/token/JSON/字段白名单/413/404/405/403；只读 DB 前后 SHA 均 `3d77b3b3...`）；`case20-refresh.json` 观察 queued/capturing/sealed/analyzing/validating/publishing/published，旧 `856e117d...`→新 `664031e4...`，重复 token 同 job，stale generation 409 `workspace_generation_conflict`，冲突 payload 409 `idempotency_conflict`，pinned_same=true；`case20-busy.json` 真实 held capturing、不同 token `refresh_busy`、cancel `cancelling→cancelled`，索引数不变；`case20-restart.json` token 轮换后旧 token 拒绝/新 token 通过，9 个索引，latest `664031e4...`，旧/新配置均可查，comparison `3c7fb689...`，active_attempts=0；`chromium-stale.log` 2 passed（pair/snapshot 切换清除旧图/旧源并中止延迟请求）。 |
| 21 | 非本轮范围 | 明确为 M2-B 缓存复用/加速，不属于 M2-A；没有实现、没有宣称、没有作为本轮通过条件。 |
| 22 | PASS | scope 移除 vs 物理删除：`r5-scope-diff-symbols.json` 35 项中 beta 保留 `shared.hpp` 声明时是 `definition_removed`，`coverage_change='out_of_scope'`，definition_range 为 None，units alpha.cpp+main.cpp；9 项 `out_of_scope`；`r5-scope-diff-calls.json` 13 项中 7 个 `relation_out_of_scope`（含 dropped beta.cpp 的 cycle_alpha→alpha、lambda→LocalThing::get）+ 6 个 `unmatched_sites`；共享实体观察保留；没有 `symbol_removed`。后续物理删除 `r5-delete-diff-symbols.json`/calls 为 0、files 为 beta.cpp `file_removed`；此前 scope 已移除，没有在 scope 内实体，故不是伪删除。 |

**结论：** 01–04、06–14、16–20、22 通过；05、15 失败；21 不在本轮。必需合同并非全部通过，故不能 ACCEPT。

## 5. 新证据复核：definition_context_changed（Codex 探针与本轮独立 fixture）

### 5.1 合同原文与实现位置

`architecture.md:129` 明文要求：

> “Protocol3 adds validated Clang definition source ranges ... Preserve ODRHash as a nonauthoritative hint only. ... A changed macro/config/read-set with identical definition bytes is `definition_context_changed` (possible effective change, with exact changed inputs), not falsely unchanged. Literal changes must be detected even when call edges and USR stay identical. Unknown range means `definition_comparison_unavailable`; an ODR hash match cannot fill the gap.”

`acceptance.md:13`（case05）要求宏/配置头变更后消费者被失效，并由 `definition_context_changed` 解释 input/config 原因；`acceptance.md:30`（case22）与 `architecture.md:131` 进一步要求 scope/删除保守。

实现实际触发点：

```python
# backend/codeweave/diff.py:108-117
old_range, new_range = x.get('definition_range'), y.get('definition_range')
if old_range and new_range and old_range['sha256'] != new_range['sha256']:
    event('symbols','definition_text_changed',usr,before,after)
elif bool(old['definition_file']) != bool(new['definition_file']):
    event('symbols','definition_added' if new['definition_file'] else 'definition_removed',usr,before,after,
          coverage_change='out_of_scope' if not new['definition_file'] and removed_scope(a,b,usr) else None)
elif old['definition_file'] and (not old_range or not new_range):
    event('symbols','definition_comparison_unavailable',usr,before,after,confidence='unavailable')
elif old['anchors'].get('definition_odr') != new['anchors'].get('definition_odr') or a['meta']['profile_id'] != b['meta']['profile_id']:
    event('symbols','definition_context_changed',usr,before,after,confidence='input-context, not runtime behavior')
if tuple(before[k] for k in ('file','line','column')) != tuple(after[k] for k in ('file','line','column')):
    event('symbols','location_changed',usr,before,after)
```

`_side()`（`diff.py:27-50`）只加载 symbols/anchors、`symbol_units`、`symbol_evidence`、calls、snapshot manifest；**没有加载 `unit_files` 读集或 `files.sha256`**。因此：

- 触发条件只有 `definition_odr` 变化或整个 profile_id 变化；
- ODRHash 在 `analyzer/main.cpp:213-225` 由 `clang::ODRHash hash; hash.AddFunctionDecl(definition);` 生成，合同明确说它只是非权威提示；
- 即使事件触发，payload 也没有 `changed_inputs` 字段，无法给出确切路径与前后哈希。

### 5.2 Codex 公共 CLI 探针（独立核对，不是机械采信）

- 脚本：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/probe_definition_context.py`，SHA-256 `a76d3119110be9922fe39290f179c48182d1cee0f1f48567c5bb14893545b60e`。
- 结果：`/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/definition-context-probe.json`，SHA-256 `951f8987e5b7047c290ec60e2e1c45dd154c2f3e1d0eea45bd3acbc66f8faeb2`。
- 自有 input/state：`/tmp/codeweave-context-probe-biayy7x0`；使用公共 CLI，每条命令均记录完整 argv 与 `exit_code: 0`。
- old index `d78b1f35-8cbd-470e-9ebe-104a2ee3b295`，new index `f5c94406-78f2-4e38-a424-b5a4fab4092a`；profile 两侧相同 `62f9a37eedc9f638b02cff3317ab0cbf6fb8772c72238694aa5d8fa1fd4f4328`；snapshots `7db58316...` vs `a149590f...`。
- `value.hpp` 中 `inline constexpr int probe_value=1` 改为 `2`；`probe_context_function(){return probe_value;}` 的定义字节未变。
- 结果：`diff-symbols` returned_count=0，`diff-calls` returned_count=0，`diff-files` 仅 `value.hpp` 的 `file_text_changed`；旧/新文件 SHA `835764e4...` / `bc4c6de0...`。
- 我核对了探针使用的分析器路径与 SHA：`/home/workspace/CodeWeave_dev/CodeWeave/.build/analyzer/codeweave-analyzer` 为 `b91b17afe37928da6f5f40374f20ee20e4f23f4d2505dfc417925e4e3c9b18b4`，与独立构建一致；查询该 state 的 `unit_files`，两版均包含 `main.cpp` 与 `value.hpp`。我没有声称逐条重跑 Codex 探针；我读取其 argv/退出/JSON 并核验 SHA，然后用下述不同输入独立复现同一类问题。

### 5.3 本轮自建不同 fixture（case23ctx）

输入（全部位于 `/tmp/cwaudit5/case23ctx`）：

```cpp
// proj/settings.hpp (old)
#pragma once
inline constexpr unsigned audit_scale = 4u;
enum class AuditLevel : unsigned { low = 1u, high = 9u };
```

```cpp
// proj/main.cpp (both sides unchanged)
#include "settings.hpp"
unsigned audited_context_leaf() { return static_cast<unsigned>(AuditLevel::low) * audit_scale; }
unsigned audited_context_root() { return audited_context_leaf() + 1u; }
int main() { return static_cast<int>(audited_context_root()); }
```

新 header 只把 `4u→6u`、`low = 1u→3u`（同字节长度）。真实结果：

| 项目 | old | new |
|---|---|---|
| index | `9dc8ea33-055e-4f9c-962e-1758c5378889` | `b1fbd1fe-55c9-492c-a75e-3563e7e8611c` |
| snapshot | `575c85488b4d1b3852707a293f34a7cb7060c6b3ab4bdfdf7a14f50ed11aa6a4` | `e3be3b311bb6cf6d94c7b12ac2ed61f5cf43cd79e1d2a59de87664aaa9a5ba77` |
| profile | `be097d7d...` | 同一 `be097d7d...` |
| settings.hpp SHA | `2133aa6a...` | `970a0435...` |
| main.cpp SHA | `06671967...` | 同一 `06671967...` |
| `audited_context_leaf` ODR | 2280648299 | 2280648299 |
| `audited_context_root` ODR | 4026570732 | 4026570732 |
| definition range/buffer hash | 两侧相同 | 两侧相同 |
| `unit_files` 读集 | main.cpp + settings.hpp | main.cpp + settings.hpp |

真实 CLI Diff：

- `diff-symbols`: `returned_count=0`, `items=[]`, `configuration_changed=false`，comparison `ac730d76...`
- `diff-calls`: `returned_count=0`, `items=[]`, `configuration_changed=false`
- `diff-files`: 1 项 `file_text_changed`，settings.hpp old `2133aa6a...` → new `970a0435...`
- 原始日志：`/tmp/cwaudit5/logs/case23-final-diff-{symbols,calls,files}.json`，stderr 均为 0，退出 0；摘要 `/tmp/cwaudit5/case23ctx/summary.json`。

行为证据：`behavior_old.bin` 输出 `leaf=4 root=5`，`behavior_new.bin` 输出 `leaf=18 root=19`，两者退出 0；二进制 SHA 分别 `70ae1c07...`、`5778f68d...`。也就是说，函数定义字节相同、ODR 相同、profile 相同，但运行行为确实改变，而函数级 Diff 完全为空。

### 5.4 判定：P1 必需合同缺陷，不是允许边界

**判定：P1（阻塞，NEEDS CORRECTION）。**

理由：

1. 合同不是只说“宏”；它明确写 `macro/config/read-set` 改变且定义字节相同 → `definition_context_changed`，并要求 exact changed inputs。case23 是 read-set（header 中的 constexpr/enum）改变，定义字节/范围/ODR/profile 均相同，完全符合“identical definition bytes + changed read-set”。
2. `ODRHash` 被合同明确标为非权威提示；用 ODR 相等来断言“没有上下文变化”正好违反“ODR hash match cannot fill the gap”。
3. `unit_files` 已经在两侧索引中记录了 `settings.hpp` 属于该 TU 的正读集，`files.sha256` 也有前后哈希；最小修正不需要新的分析器字段或大规模架构。
4. formal `verify_m2.sh` 退出 0 不覆盖该缺陷：`backend/tests/test_workspace.py:87` 与 `frontend/e2e-m2/workspace.spec.ts:52` 的宏测试会改变 ODR，所以仍然触发旧的 ODR 分支；它们没有覆盖 constexpr/enum 且 ODR 不变的情况。正式脚本的 0 不能替代合同反例。

**影响：** 对一个“可用 M2-A”闭环，用户改 header 中的 constexpr/enum/read-set 后，网页/CLI Diff 会错误显示相关函数无变化；这会误导代码审查和变更筛选。即使宏 case 有事件，也缺少 exact changed inputs，用户无法从 Diff 事件知道是哪一个头/config 输入导致的。

**最小修正建议（不引入 M2-B 或新架构）：**

- 在 `diff.py` 的 `_side()` 中读取 `unit_files(index_id,source_file,path)` 与 `files(index_id,path,sha256)`；用 `symbol_units` 限定到该符号的观察/定义 TU，取这些 TU 的正读集。
- 对 matched symbol，优先保留现有分支：定义范围哈希变化 → `definition_text_changed`；范围缺失 → `definition_comparison_unavailable`；定义消失/scope → 现有 `definition_removed/out_of_scope`。
- 在定义字节相同的情况下，比较两侧读集交集内文件的 SHA-256；**排除符号自身的 definition_file**（这样同文件纯移行、范围外空行只产生 `location_changed`/`site_location_changed`，不会伪报上下文变化）。若有差异，发 `definition_context_changed`，并附：
  ```json
  "changed_inputs": [
    {"path": ".../settings.hpp", "before_sha256": "2133...", "after_sha256": "970a..."}
  ]
  ```
- 保留 ODRHash 作为额外触发/提示；当 `profile_id` 不同时，把 profile 前后值（或 `{kind:"profile", before, after}`）也放入 `changed_inputs`，不要只给 confidence 文本。
- 该修正是保守的“possible effective change”，与 architecture 的读集失效语义一致；它可能对同一 TU 内未直接使用的头变更产生保守事件，报告应明确这是 input-context，不声称 runtime behavior。若需要更精细，可后续增加 per-definition read-set，但这不作为本轮最小修复的前置条件。

**回归测试建议（只建议，未改测试）：**

1. 新 fixture：header 中 constexpr/enum 值变化，函数定义字节/ODR/profile 不变 → 消费者函数恰有一个 `definition_context_changed`，`changed_inputs` 含该 header 的前后 SHA-256；symbols/calls 无伪关系增删。
2. case05 宏头变化 → 仍有一个 context 事件，且 `changed_inputs` 含宏头 hash（或 profile 前后值）；`configuration_changed` 符合真实配置。
3. 纯移行/范围外空行 → 仅 `location_changed`/`site_location_changed`/保守 `ambiguous_correspondence`，不得出现 `definition_context_changed`。
4. literal 变化 → 仅 `definition_text_changed`，不额外发 context 事件。
5. 共享头由 a、b 消费而 c 不消费 → context 事件只出现在读集确实包含该头的符号/ TU；无关 .cpp 编辑不触发其他 TU 函数事件。
6. `-D`/profile 变化 → context 事件带 profile 前后值；`configuration_changed` 与 profile_id 一致。
7. 若采纳“排除自身定义文件”的最小方案，另加同文件外部 constexpr 的已知残余用例，明确保留文档边界，不把它伪装成已覆盖。

## 6. P0–P3 问题清单

### P0（阻塞性安全/身份/快照/核心 UI 崩溃）

**无。** 本轮没有发现可复现的 P0。安全负例、封存/快照、旧指针、HTTP 鉴权、旧源隔离均保持；没有发现越界读取、命令执行、Git hook 执行或半索引发布。

### P1（必需合同缺陷，阻塞）

- 位置：`backend/codeweave/diff.py:116`（触发条件仅 ODR/profile）；`diff.py:27-50`（未加载读集/文件哈希）；`analyzer/main.cpp:213-225`（ODR 仅提示）。
- 触发：header 中 `inline constexpr`/enum 值变化，函数定义字节、范围、ODR、profile 不变。
- 证据：`/tmp/cwaudit5/case23ctx`（old/new index 如上；symbols/calls 0；files 1；行为 4/5→18/19）；Codex 探针 `definition-context-probe.json` 同类；`unit_files` 两侧均含 header。
- 影响：Diff 把真实行为变化报告为“无函数变化”；宏事件也缺少 exact changed inputs。
- 修正：见 5.4 的最小修正。
- 回归：见 5.4 的 1–7。

### P2（真实输出边界缺陷；本审核按 case15 原文判失败）

- 位置：`backend/codeweave/index.py:543`
  ```python
  return {"index_id": active, "path": value, "start_line": start_line, "end_line": end_line,
          "content": content.decode("utf-8", errors="replace")}
  ```
- 触发：索引文件包含非 UTF-8 字节（case15bad 的 `0xFF`）。
- 证据：源文件 61 bytes、SHA `15f2e9e051325146407c36895472c96f0f54fc5e40ce825abbfccc89cb920029`；CLI `c15bad_source.json` 与 HTTP `c15bad_http_source.json` 均返回 U+FFFD，重新编码后 63 bytes、SHA `99d4aec9575fe0a2de53b07dc036bc20553c5640b74ef0409f3be578459c2bb3`。服务没有报错，而是静默改变字节。
- 影响：用户看到的源码与索引字节/SHA 不一致；无法进行可信的 source 核验；对含非 UTF-8 注释/字面量的 C++ 工程不满足“original indexed byte slices”。
- 修正（最小、非大架构）：
  - 严格 `content.decode('utf-8')`；失败时返回明确错误 `source_not_utf8`（HTTP/CLI 保留 `{error:{code,message}}`），不要静默替换；或
  - 增加字节安全的 `content_base64`/`content_encoding` 字段，并让所有调用方按编码解码；无论选哪种，都必须让 served bytes 的 SHA-256 等于索引文件/范围 SHA。
- 回归：构造含 `0xFF` 的 source，断言要么明确失败且不伪造内容，要么字节级 base64 往返 SHA 相等；覆盖 HTTP 与 CLI；验证 `files.sha256`/range hash 与返回内容一致。

### P3（低级输出完整性/可验证性缺陷，非独立阻塞）

- 位置：`backend/codeweave/app.py:123-126`（`/api/source` 原样返回，无 hash envelope）；`app.py:202-209`（`/api/source-diff` 直接返回 `source_diff`，无 hash envelope）；`index.py:543` 的 source payload 只有 `content,end_line,index_id,path,start_line`。
- 触发：任何 source/source-diff 查询。
- 证据：`c15_source_a_final.json` 的键集合为 `['content','end_line','index_id','path','start_line']`；`c15_diff_source.json` 键为 `comparison_id,left,right,left_index_id,right_index_id,unified_diff,windowed`，嵌套 content 无 SHA；而 `c15_diff_files.json`/`c15_diff_symbols.json` 有两侧整文件/范围 hash。
- 影响：source 响应本身不可直接验证是否等于索引字节；case15“serve ... and hashes”只能跨 endpoint 拼合，且与 P2 叠加时用户无法发现替换。
- 修正：在 `/api/source` 与 `/api/source-diff` 的 envelope 增加整文件 `sha256`、范围 `range_sha256`/`buffer_sha256`（复用 `files.sha256` 与 `definition_range` 数据），并保持现有预算；前端/CLI 展示/校验这些字段。
- 回归：source 响应 `sha256` 与 `files` 表/差异事件哈希一致；窗口截断时区分 whole-file 与 range hash；非法字节按 P2 策略处理。

### 非问题/已澄清项

- `r5-delete-diff-symbols.json`/calls 为 0 不是删除漏报：该 fixture 先移除了 beta 的 TU scope，scope 内已无实体；后续物理删除只在 files 产生 `file_removed`，没有虚假 `symbol_removed`。
- case16 自有哨兵 mtime 变化归因于审核者自己的控制命令，不是产品 hook；详见 4 的 case16 行。
- 候选目录 9 个 `.pyc` 是审核导入生成的非清单附加物，不是候选源文件变化。
- 正式 suite 的 `132 passed` 与 `VERIFY_EXIT=0` 真实有效，但测试覆盖没有 case23 的 ODR 不变读集场景，故不能推出 case05 PASS。

## 7. 边界、限制与未覆盖

1. **只读边界**：候选、源码仓库、DevFlower、旧任务均未改；未执行 commit/push/merge/rebase/reset/clean/stash/tag；未发布。只在 `/tmp/cwaudit5` 与 `round-5/audit` 写自有数据/报告。
2. **候选无 `.git`**：候选是 84 文件的快照副本；Git mode 用文件可执行位按 manifest 规则核验，不能等同于从 Git index 读取 mode。原始源码仓库 HEAD/base/branch 另行只读核验。
3. **9 个 pycache 附加物**：审核导入候选模块产生，位于候选目录但不在 manifest；未删除；不改变 84 文件字节/mode。报告末次核验会再次列出。
4. **读集精度**：现有 `unit_files` 是 TU 级 positive read-set，不是完整 include-resolution 依赖模型；P1 的最小修正按 TU 读集做保守 input-context 提示，可能对同一 TU 内未实际使用的头变化给出保守事件。更精确的 per-definition read-set 不在本轮实现范围；不能把该近似说成精确运行时因果。
5. **同文件外部常量残余**：若“排除自身 definition_file”以保护纯移行，则同一 .cpp 内被函数使用的外部 constexpr 变化仍可能漏报；这是最小修正的已知残余，应文档化或用可选的 per-definition read-set 后续解决，不应在本轮假装已覆盖。
6. **ODRHash 非权威**：任何“ODR 相同即无变化”的推断都不成立；P1 正是该问题。
7. **P2/P3 的合同解释**：case15 指定字符集是合法 Unicode/emoji/combining + CRLF，这些正例通过；但合同文字“original indexed byte slices and hashes”没有限定 UTF-8，且 `0xFF` 是真实 C++ 源字节，故本审核从严把 P2/P3 记入 case15 FAIL。若产品明确声明“仅支持 UTF-8 源文件并在入口拒绝非 UTF-8”，则应把该限制写入合同/错误协议，而不是静默替换；当前没有这样的声明。
8. **Codex 探针**：读取并核验了脚本/结果 SHA、argv、退出码、JSON 与 `unit_files`；没有逐条重跑其全部命令。用不同 fixture（case23ctx）独立复现，满足“可以确认或反驳、但必须自有证据”的要求。
9. **既有正式验证**：`verify_m2.sh` 使用 `/tmp` 工作副本和新构建，`VERIFY_EXIT=0`；JUnit `132/0/0/0`、fixture、38 前端、7 M1 + 1 M2 Chromium 均真实。它不覆盖 P1 的 ODR 不变读集反例，也不覆盖 P2 的非法字节/源哈希 envelope。
10. **未扩大到**：全隐式调用、PCH/modules、全程序虚分派、M2-B、任意历史构建、私有大型项目、RMC/F11/reference/凭据/网络上传，均未触碰，也不在本轮结论内。
11. **历史/旧结论**：没有沿用任何旧 ACCEPT；round-2/3/4 的中断/失败记录保留；本轮只把本次真实证据作为裁决依据。
12. **演示服务**：父 Agent 的 8000 端口服务未被触碰；本轮 18091/18097 等服务已停止，case20 结论来自保存的真实 HTTP 输出与 Chromium 日志。

## 8. 首末 84 文件身份核验

### 8.1 报告前快照

```text
/tmp/cwaudit5/logs/final_manifest_pre_report.json
  manifest_sha256 = ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb
  expected = 84
  actual = 93
  missing = []
  sha_mismatch = []
  mode_mismatch = []
  unexpected_count = 9
  total_expected_bytes = 478142
```

`sha256sum -c candidate-manifest.sha256` → `candidate-manifest.json: OK`，退出 0。额外 9 个 `.pyc` 均已列出，均为审核导入生成、非 manifest 文件；84 个受审文件全部通过字节与 mode 核验。

### 8.2 报告落盘后复核

见本报告末尾的实时追加块（本块在 report.md 写入后生成，使用同一 `/tmp/cwaudit5/verify_manifest.py` 与 `sha256sum -c`）。

## 9. 最终裁决

**NEEDS CORRECTION。**

- P1：`definition_context_changed` 只依赖 ODRHash/profile，漏报 read-set/constexpr/enum 变更，且事件无 exact changed inputs；已用两个独立 fixture（Codex 探针核对 + 本轮 case23ctx）复现，违反 `architecture.md:129` 与 `acceptance.md:13`（case05）。
- P2/P3：非 UTF-8 source 被静默替换，source/source-diff 缺少哈希 envelope；按 case15 原文判 FAIL，属于真实输出边界缺陷。
- 正式验收 `VERIFY_EXIT=0` 是真实的，但不能抵消合同反例；不把它当作 ACCEPT。
- 关键证据充分，缺陷可复现，故不是 BLOCKED；不能给 ACCEPT 或 ACCEPT WITH LIMITATIONS。


### 8.3 报告与 result.json 落盘后的末次核验

在 `report.md` 与 `result.json` 均落盘后、且在追加本节之前，执行同一 `/tmp/cwaudit5/verify_manifest.py`：

```text
FINAL_VERIFY_RC=0
{
  "root": "/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/candidate",
  "manifest": "/home/workspace/CodeWeave_dev/m2-usable-beta-20261020/round-5/candidate-manifest.json",
  "manifest_sha256": "ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb",
  "expected": 84,
  "actual": 93,
  "missing": [],
  "sha_mismatch": [],
  "mode_mismatch": [],
  "unexpected": [
    "backend/codeweave/__pycache__/__init__.cpython-312.pyc",
    "backend/codeweave/__pycache__/__main__.cpython-312.pyc",
    "backend/codeweave/__pycache__/cli.cpython-312.pyc",
    "backend/codeweave/__pycache__/diff.cpython-312.pyc",
    "backend/codeweave/__pycache__/git_snapshot.cpython-312.pyc",
    "backend/codeweave/__pycache__/index.cpython-312.pyc",
    "backend/codeweave/__pycache__/schema.cpython-312.pyc",
    "backend/codeweave/__pycache__/snapshot.cpython-312.pyc",
    "backend/codeweave/__pycache__/workspace.cpython-312.pyc"
  ],
  "unexpected_count": 9,
  "total_expected_bytes": 478142
}
STDERR_BYTES=0
```

- `manifest_sha256` 精确等于要求的 `ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb`。
- `missing=[]`、`sha_mismatch=[]`、`mode_mismatch=[]`：**84/84 个 manifest 文件字节 SHA-256 与 Git mode 全部匹配**。
- 9 个 extra 全部是审核导入生成的 `backend/codeweave/__pycache__/*.pyc`，不在 manifest；没有删除（删除会改变候选），也没有冒充受审文件。
- 该输出与 `/tmp/cwaudit5/logs/final_manifest_after_result.json` 逐字段相同；保存为 `/tmp/cwaudit5/logs/final_manifest_final.json`。
- `sha256sum -c candidate-manifest.sha256` 在 `round-5` 目录再次返回 `candidate-manifest.json: OK`，退出 0。
- 本节只追加审计报告文字，未再写入候选；`result.json` 的最终 SHA-256 为 `aac2e391dbd61b773b9ae9a93955224c32c2fea897764e474fd3698009cc70db`。

**最终身份结论：** 候选 84 文件在报告开始前与全部报告/结果落盘后两次独立逐文件核验一致；清单 SHA-256 未变；候选目录仅多出 9 个审核生成的 pycache 非清单附加物。身份层面无阻塞。
