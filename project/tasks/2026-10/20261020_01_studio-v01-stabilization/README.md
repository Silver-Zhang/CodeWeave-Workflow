# Studio v0.1 稳定化修复与独立验收

任务 `20261020_01_studio-v01-stabilization`，B 模式；最终结论 **ACCEPT**。本任务完成实施、自验、真实独立复审及指定开发分支交付；用户最终验收与 main 合并仍是独立关口。机器摘要和各轮原始裁决字段见 [evidence.json](evidence.json)。

## 1. 目标与范围

**A. 当前版本**

修复 Studio 编译竞态、验证节点状态与候选轮次归属，并完成普通 HTTP/Chromium、真实双 Agent clamp 任务和固定外部监督审核。只修改 DevFlower，未修改 CodeWeave/RMC 或 project/codeweave。

| 对象 | 最终身份 |
|---|---|
| 源码分支 / PR | `flow/studio-mvp` / [PR #3](https://github.com/Silver-Zhang/DevFlower/pull/3) |
| 修复前 | `a93ed81170ead88f78ab7e3e9f9d57ab9594c407` |
| 修复后 | `ab6ea154e795ecd8ff57dd3c6181c6c3835d1816` |
| 当前候选 SHA-256 | `0ac41811de05565109482397c112064316fef7df7dffaa606e656182e890ba1d` |
| 被审且已提交 Git tree | `25c9cc4ceb30741d9f4fad44872106798d14b285` |
| 合同 SHA-256 | `575888a0911c5f37fe2319fa009916d48c206bfabd45a62493aa12cc05fb7879` |
| Controller SHA-256 | `06eb6d8be79f722b7f8600083f60c2dd6e8d5316de948b1f877cb01a8be0bebc` |

源码开发工作树为 `Studio-stabilization/`；`DevFlower/` 保留 Controller 分支 `2e298e4`，`Studio-validation/` 保留旧验收基线。自身档案仅在 `records/project/`，原始大日志在工作区 `archives/studio-v01-stabilization-20261020/`。这些是同一 DevFlower Git 仓库的独立工作树。CodeWeave 工作区的业务仓库及 DevFlower project/codeweave 实例均保留。

PR #2 尚未合并，PR #3 仍为 Draft，base 保持 `flow/multi-agent-orchestration`。main 未合并两项更新；没有改写共享历史。

## 2. 做法与证据

**B. 修复总结**

| 缺陷 | 原始复现与最终机制 | 独立结论 |
|---|---|---|
| ST-R01 P1 | 普通 Chromium 复现旧 A 响应重新启用可见 B 的启动。现以编辑版本、请求序号及完整 task/document 快照绑定编译；所有编辑/导入/新建/加载失效，启动前重核，后端继续独立授权。 | CLOSED |
| ST-R02 P2 | 旧真实 SQLite/WAL 中同 argv 两项均显示 pending。现按 run/round/verification/operation 关联，EXITED 后先 executed，结果计数校验后才 passed/failed；每项即时投影。 | CLOSED |
| ST-R03 P2 | round 2 IMPLEMENTING 错示 round 1 候选。现记录 candidate_round，当前候选和 previous_candidate 分列；旧审核/计数不冒充本轮。 | CLOSED |
| F-01–05 | 编辑器超限/不支持 ID 明确拒绝、监控不截断；运行标题更新；异步初始化兼容 Node18；原 ID 匹配防止失败变绿；沙箱拒绝测试增加成功启动正对照。 | CLOSED |
| SELF-R01 P1 | 第1轮补充自验发现无效可见 argv 仍能编译旧配置并启用启动。第2轮以字段有效性阻止编译/保存/导出/启动；纠正字段后正常恢复。审核者独立重现旧故障并验证新行为。 | CLOSED |
| F-06 P3 | 第1轮审核发现生成显示 ID 可与合法原 ID 冲突。第2轮给所有可见验证标签加唯一计划序号，内部仍按原 ID 匹配状态。 | CLOSED |

12 个明确源码路径：`docs/STUDIO.md`；`tests/host_isolation.py`、`studio_races.py`、`studio_races.cjs`、`test_studio_progress.py`；`tools/orchestration/controller.py`、`process.py`、`verification.py`；`tools/studio/graph.py`、`projection.py`、`server.py`、`static/app.js`。未放宽 Controller 授权或交付 Gate，验证增量事件不加入 argv、源码或凭据。

**C. 实际测试**

| 验证 | 最终结果 | 退出码 / Skip |
|---|---|---|
| 全量 unittest（含 Studio 35、进度8、旧 Engine/API/SQLite 回归） | 132/132，0 failure/error | 0 / 0 |
| `check --baseline`、Node18 JS 语法 | 通过 | 0 / 不适用 |
| 宿主隔离 | 4/4 | 0 / 0 |
| 仓库普通 HTTP/Chromium 竞态回归 | 9/9 | 0 / 0 |
| 完整普通浏览器交互与真实任务 | 23/23；没有 offline bridge | 0 / 0 |
| 模拟 CLI + 真实 Controller/SQLite 故障 | 11/11；不是模型验收 | 0 / 0 |
| 独立审核重跑全量 | 132/132 | 0 / 0 |
| 独立构造进度/Gate、bare remote、启动、浏览器 | 14 + 4 + 2 + 24 项全部通过 | 各 0 / 0 |
| 独立真实 WAL 并发 | 1 writer + 3 reader，360 一致快照 | 0 / 0 |
| 原六项 clamp 测试 | 两次真实任务均6/6 | 0 / 0 |

两次真实 clamp：`a7e0f622fb7143cd9a91daff5ffaaee7` 和 `c0f91c11524c49f09606e13df1b9f9cd`，均 READY round1，原6项测试0失败/错误/Skip，独立 DeepSeek ACCEPT；commit/push 全关。第2次 Controller 哈希与最终框架候选一致。真实进程/会话/退出码在 evidence.json，完整 SQLite、候选和验证报告本地保留。第1次浏览器/API曾观察到完整阶段含 GATING；第2次短暂 GATING 未被轮询捕捉，不冒称所有阶段都被实时看到。

Codex CLI 0.163.0，请求 `gpt-6.1-sol/xhigh`，resolved model/effort 缺失为 unknown。Claude Code 2.1.303，实际模型 `deepseek-flash[1m]`，请求 `max`，resolved effort unknown。Python3.12.3、Git2.43、Node18.19.1/22.14.0、Chromium156.0.8078.4、bwrap0.9.0、Landlock ABI8。

可运行命令：`python3 tools/devflower_studio.py --workspace <新的独立目录>`；`--control <控制目录>` 只读监控；明确 `--launch-task` 与 `--authorization` 可启动一次匹配任务。CLI 的 init/new/index/check 和 doctor/run/status/resume/cancel/audit/deliver 保持兼容。新增竞态验证入口 `python3 tests/studio_races.py --chromium <路径> --artifacts <新目录>`，可用 `--node` / `--playwright-module` 绑定已安装测试工具。运行说明见源码 `docs/STUDIO.md`。

## 3. 决策记录

**D. 真实多 Agent 审核循环**

用户附件批准一次启动、连续修复/全量验证/独立审核及满足条件后的指定分支交付；后续指定 DeepSeek max，审核 cwd `/home/workspace/DevFlower`。固定外部监督，候选源码/证据只读、测试区可写。待审 Controller 是被测对象，没有批准或推送自身。

同一明确审核 UUID：`ed0a5ce5-2478-4577-bf8b-ee05413a7f31`；第2轮用 `--resume`，不猜测 `--last`，不复用其他项目会话。

| 轮次 | 候选 | 原始 DeepSeek 裁决与实际进程 | 外部处理 |
|---|---|---|---|
| 1 | `0eb8b38d8c4b6eb630c425c6fc83e8015d54168cb0b817810193f17f5c1bc049` | ACCEPT；F-06 P3 OPEN 非阻断；902.28秒、exit0、无超时 | Codex补充发现SELF-R01，外部判NEEDS_CORRECTION，未交付；修复两项后全量重验新候选。 |
| 2 | `0ac41811de05565109482397c112064316fef7df7dffaa606e656182e890ba1d` | ACCEPT；ST-R01–03、F-01–06、SELF-R01全部CLOSED；682.56秒、exit0、无超时 | 原始新候选裁决通过；外部148项确定性核对通过后交付。 |

审核者明确保留限制：没有再次付费调用夹具模型，而是独立核验真实运行DB/候选/会话并重跑6测试；完整23项和11项模拟原脚本未放入冻结审核材料，原结果作为证据，审核者另构造44项代表性动态检查并重跑仓库9项竞态及全量132项。嵌套沙箱 bwrap 不可用，审核内 `host_isolation` 实际 exit1（2 failures、2 errors）完整保留；审核者设计的脚本交固定无凭据宿主 runner 实际执行4/4 exit0，再交其裁决。不是把环境失败改写为通过。

旧 `studio-v01-validation` 的 ACCEPT_WITH_LIMITATIONS 及验收方 NEEDS_CORRECTION 均保留。第1轮报告中凭据/浏览器依赖表述不准确之处由外部 assessment 指正，原文未改；第2轮正确区分审核 CLI 的已批准服务凭据、Node Playwright、额外模型调用与夹具证据。

## 4. 结论与边界

**E. 最终验收：ACCEPT。** 当前候选可作为单人本地 Studio v0.1 使用，完成真实双 Agent clamp 闭环、普通浏览器与 Controller 一致性验证，具备技术冻结条件。53文件、完整候选、合同、Controller版本和被审 Git tree 均核对一致；所有必需缺陷关闭。

源码 `ab6ea154e795ecd8ff57dd3c6181c6c3835d1816` 已经正常快进并读回；本地53文件和index/tree一致、工作树干净。原生Git推送dry-run因本机HTTPS凭据不可用失败，未改动远端；最终沿用已授权GitHub连接，以 expected SHA 和 force=false 普通快进，再原生fetch验证。档案在独立 `project/devflower` 提交，最终远端收据由本地 `delivery-summary.json` 记录；两分支不冒称原子交付。

PR #3 保持 Draft，仍依赖未合并 PR #2；技术上可转 Ready for Review，但当前不宣称已获 main 合并许可或主线 READY_TO_MERGE。用户后续决定是否转正式评审及合并顺序。未 merge、tag、release、force、delete。

剩余限制：编辑器仅支持1–20顺序验证及受限ID；旧在途记录缺candidate_round时进度保守显示未归属/pending；不安全原ID显示序号加unknown但状态匹配正确；产品交付backend限本地bare remote，真实业务任务/外发/交付各需独立授权；服务为本地单人使用，实际effort缺失仍unknown。以上不改变本轮ACCEPT原意或放宽未来任务权限。

## 5. 过程记录

2026-10-20：核对并保护所有原有工作树及云端状态；复用上轮可核验证据；旧基线124/124、host4/4通过，Node18原始syntax exit1保留；复现ST-R01–03/F-04，实施第1候选后131/131、竞态8/8、交互23/23、模拟11/11及真实clamp通过。第1轮实际ACCEPT后仍因SELF-R01暂停交付；修复后第2轮132/132及全部必需验证、真实复审完成，条件满足后交付源码和本任务记录。

历史执行错误保留：进度测试夹具起初把JSON误声明JUnit；辅助授权采集两次误用返回类型；第一次冻结采集缺config_sha256字段，未完成目录保留；任务README最初标题不符合旧check后恢复五节；第1轮独立浏览器脚本两处断言/选择器问题修正后重跑。均未修改验收条件或掩盖失败。

默认Claude历史起初没有此对话，因为审核使用专用HOME。已只为本项目审核UUID添加默认历史的原生符号链接（硬链接因跨文件系统失败）；链接存在及目标可读已验证，未复制会话全文、未更改全局认证或其他会话；界面历史列表未视觉验证。在 `/home/workspace/DevFlower` 可明确运行 `claude --resume ed0a5ce5-2478-4577-bf8b-ee05413a7f31` 查看。

原始日志/截图/SQLite/固定候选/进程收据仅存本地 archives；档案仅此五节README和必要机器摘要。完成本次Studio v0.1后停止，未自动进入v0.2或CodeWeave下一阶段。
