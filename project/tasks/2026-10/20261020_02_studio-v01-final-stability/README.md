# Studio v0.1 最终身份竞态稳定化

任务 `20261020_02_studio-v01-final-stability`，B 模式。最终结论 **ACCEPT**，全部阻断项关闭，满足本轮技术冻结/READY_TO_MERGE条件；main合并许可与PR依赖处理仍为人工关口。必要机器摘要及原始裁决字段见 [evidence.json](evidence.json)。

## 1. 目标与范围

修复ST-R04保存响应污染其他草稿、ST-R05运行快照污染其他选择。只改UI、测试和说明，不重构Controller、不新增执行接口、不开发Studio下一代。

| 版本 | HEAD / tree / candidate |
|---|---|
| 修复前HEAD | `ab6ea154e795ecd8ff57dd3c6181c6c3835d1816` |
| 修复后HEAD | `4636083073b39b6e1f42f4544f7b3d35d4f32140` |
| 修复前tree | `25c9cc4ceb30741d9f4fad44872106798d14b285` |
| 修复后被审且已提交tree | `1dc790d5e259821570b0f79d62cc25dc77bc3d1d` |
| 修复前候选SHA-256 | `0ac41811de05565109482397c112064316fef7df7dffaa606e656182e890ba1d` |
| 修复后候选SHA-256 | `af66e5c0dc5b4f8855933c26834b9c2714eb1b03daf41a0d23e3a9d243e929b0` |
| 本轮合同SHA-256 | `f851df710f325dd50b58e2ea3671a6aee39251671845093ebe1c6429c08cf49f` |

源码开发工作树 `Studio-stabilization/`，分支 `flow/studio-mvp`，目标 [PR #3](https://github.com/Silver-Zhang/DevFlower/pull/3)。PR #3仍Draft、base为`flow/multi-agent-orchestration`，PR #2尚未合并。其他DevFlower工作树、CodeWeave/RMC及project/codeweave未修改。自身记录仅`records/project/`，原始日志、截图、固定源码、进程收据仅在本地`archives/studio-v01-final-stability-20261020/`。

## 2. 做法与证据

ST-R04：旧基线真实Chromium/HTTP中，保存A的响应延迟到新建B之后，随后B保存请求确实携带A的ID。现在请求捕获草稿代次、ID/revision、文档与编辑版本；同草稿保存串行，旧响应只能刷新历史；当前仍有编辑或未提交字段时明确提示未保存。加载/新建/导入变更草稿代次。后端不可变revision与CAS保持原样。

ST-R05：旧基线中选中B后释放A快照，出现B的run_id搭配A节点、6测试、Round2和ACCEPT。现在请求绑定run_id和代次，并验证返回snapshot.id；旧成功、失败及finally不能覆盖当前请求。切换/当前网络错误清空旧快照，标题、节点、轮次、计数、检查器及历史由同一快照渲染。没有修改Controller权威状态。

仅4个源码路径变化：`tools/studio/static/app.js`、`docs/STUDIO.md`、`tests/studio_identity_races.py`、`tests/studio_identity_races.cjs`。Controller/backend字节与基线相同；Controller哈希仍`06eb6d8be79f722b7f8600083f60c2dd6e8d5316de948b1f877cb01a8be0bebc`。

| 实际验证 | 测试/失败/错误/Skip | 退出码 |
|---|---|---|
| 基线新增两项主复现 | 2 / 2 / 0 / 0（预期旧缺陷） | 1 |
| 基线全量单元 | 132 / 0 / 0 / 0 | 0 |
| 当前全量单元（含Studio35、进度8、SQLite/WAL与旧内核） | 132 / 0 / 0 / 0 | 0 |
| 当前宿主隔离 | 4 / 0 / 0 / 0 | 0 |
| `check --baseline`、Node18 JS语法 | 结构/语法检查通过，计数不适用 | 各0 |
| 仓库既有普通Chromium/HTTP竞态 | 9 / 0 / 0 / 0 | 0 |
| 新增保存/监控竞态 | 17 / 0 / 0 / 0 | 0 |
| 审核者重跑全量/既有竞态/新增竞态 | 132、9、17；各0失败/错误/Skip | 各0 |
| 审核者独立基线反例 | 23 / 19 / 0 / 0（预期旧缺陷） | 1 |
| 审核者独立当前候选反例 | 23 / 0 / 0 / 0 | 0 |
| 审核者另构造进度/Gate、Launcher、HTTP权限面、Landlock | 5、11、12、3；各0失败/错误/Skip | 各0 |

新增与独立反例覆盖延迟/逆序保存、切换/新建/导入、同草稿并发、持续编辑和未提交输入、实际CAS冲突、A→B→A、逆序列表/快照、旧/当前网络失败与超时、返回ID不符、旧进程记录、设计/监控隔离。独立复查ST-R01–03、SELF-R01、F-06均CLOSED；A07/A08/A09/A12/A13/A16代表性旧门禁测试通过。

运行新增测试：`python3 tests/studio_identity_races.py --chromium <Chromium路径> --artifacts <新目录>`；可用`--node`和`--playwright-module`指定已安装Node工具。全部浏览器使用普通Chromium+真实HTTP，无offline bridge。Python Playwright未安装，旧可选`studio_browser.py`没有重跑，不能声称其通过。Python3.12.3、Node18.19.1/22.14.0、Chromium156.0.8078.4、bwrap0.9.0、Landlock ABI8。没有新付费clamp模型试验；旧模型运行只作历史，不冒充本候选新证据。

## 3. 决策记录

用户本次要求自动修复、完整自验、真实Claude独立审核、有界迭代与指定分支条件交付；沿用本对话已批准DeepSeek/max及cwd。没有新增会话中心或第三Agent。新Controller不是自身验收裁判。

本轮共 **1轮正式审核**：候选`af66e5c0dc5b4f8855933c26834b9c2714eb1b03daf41a0d23e3a9d243e929b0`，真实Claude Code2.1.303，经已批准路由实际模型`deepseek-flash[1m]`，请求effort=max，resolved effort无字段，记unknown。会话`ed0a5ce5-2478-4577-bf8b-ee05413a7f31`明确resume；PID`358905`、start`103227895`，耗时669.44秒，exit0，无超时；原始裁决 **ACCEPT**。ST-R04、ST-R05 CLOSED，其余必需复查项全部CLOSED，无未关闭阻断项。本轮无需第二候选，未复用旧ACCEPT。

固定外部监督先冻结完整55文件、合同和tree，再以只读副本组织审核；审核者独立重建文件/Git blob/tree/Controller身份、执行反例，最后阅读实施总结。原始结果哈希`bb6ee1632328853862b4be5ec1d71cdbd30dfe9dcc965f95d6bc931eab0601bb`，外部82项确定性核对通过后才交付。

审核沙箱嵌套bwrap失败（exit1、2 failures、2 errors）保留。审核者独立编写宿主脚本，由固定无凭据runner冻结脚本并实际执行4/4、exit0，再交审核者判断；不把环境失败记为PASS。独立浏览器脚本初次22用例有2项导入用例断言失败；后续以实际服务端A/B不同ID和原文档保持不变核验合同，最终23/23通过。初始日志和各次结果保留，产品源码在审核期间未改。

**原生会话管理**：HOME=`/home/workspace/DevFlower/archives/studio-v01-stabilization-20261020/runtime/independent-reviewer`；配置根=`/home/workspace/DevFlower/archives/studio-v01-stabilization-20261020/runtime/independent-reviewer/.claude`；cwd=`/home/workspace/DevFlower`；原生记录=`/home/workspace/DevFlower/archives/studio-v01-stabilization-20261020/runtime/independent-reviewer/.claude/projects/-home-workspace-DevFlower/ed0a5ce5-2478-4577-bf8b-ee05413a7f31.jsonl`。这是沿用的持久专用HOME，不是临时测试目录；不得按临时产物清理。未复制整个~/.claude、未覆盖全局认证与其他项目会话。CLI已实际用同一resume命令完成本轮，终态session_id一致；原生文件存在，未读取/导出其全文。

明确恢复命令：

```sh
cd /home/workspace/DevFlower
HOME=/home/workspace/DevFlower/archives/studio-v01-stabilization-20261020/runtime/independent-reviewer /home/silver/.local/share/claude/versions/2.1.303 --resume ed0a5ce5-2478-4577-bf8b-ee05413a7f31 --model deepseek-flash[1m] --effort max
```

## 4. 结论与边界

**ACCEPT；ST-R04/ST-R05已关闭，Studio v0.1具备技术冻结条件。PR #3达到本轮READY_TO_MERGE技术条件，不等于获准执行合并。** PR #3保持Draft及对未合并PR #2的依赖。下一步需要用户决定转Ready for Review，以及PR #2独立合并后核验/调整PR #3依赖与主线集成顺序；不得因本轮通过自动合入main。

源码已交付`4636083073b39b6e1f42f4544f7b3d35d4f32140`，远端读回及55文件/tree一致，本地干净。使用已授权GitHub连接以expected SHA、force=false正常快进，再原生fetch核对；没有reset/force/历史重写。项目记录另提交project/devflower，最终各分支收据在本地delivery-summary.json；不冒称跨分支原子交付。技术验收与用户最终验收分开。

原始审核保留以下非阻断限制：启动后新run行尚未出现时可能自动选中已有运行，其自身id/state仍正确；保存成功后的历史列表刷新失败会静默保留旧列表；保存回执丢失后本地CAS基准可能过期，下次通过409处理，避免静默覆盖。单人本地使用范围、编辑器语法子集与独立业务授权要求沿用既有合同。未扩大授权、增加浏览器执行接口或改变Controller。

## 5. 过程记录

2026-10-20：核对本地/远端基线ab6ea15及全部工作树无修改；建立本任务，先用真实浏览器留下两个基线失败，再做最小UI修复。当前132项全回归、host4、旧竞态9、新竞态17通过后冻结；真实DeepSeek独立复现旧版、验证新版并给出ACCEPT；外部确定性检查与精确tree核对通过后正常交付。源码、合同与待审范围始终未变。

上一任务及其两轮原始裁决、失败和全部档案保持不变。本轮过程材料集中archives，本任务只保留此五节README、task.json和必要机器证据，INDEX由原工具生成。CodeWeave/RMC及project/codeweave未改动。完成本轮技术验收即停止，不进入Studio下一代，不合并、删分支、tag或release。
