# Issue14：工作台视觉与运行证据

任务 `20261024_01_issue14-ux-polish`，B模式。版本与机器证据见 task.json、candidate-manifest.json、evidence-summary.json。

## 1. 目标与范围

按 [Issue14](https://github.com/Silver-Zhang/DevFlower/issues/14) 与本次用户指令，让普通用户能直接识别运行状态、等待原因、真实交接和下游请求，改善画布与会话阅读。沿用 React Flow、Controller、授权与交付门禁，不扩展 Provider、不修改 CodeWeave/RMC、不合并 main、不升级 Stable。

实施前核验 main e35dec13825ecbce39ae4092c3d94a059bc732b8/tree a0c16fa6dccf9ad9fd9c7d52cd9495ada4db24d5，PR10/11/13均已合并，六个既有工作树干净、主线CI成功。新建独立 development/issue14-ux，flow/workbench-ux-polish。现有分支、原生会话、原Stable5816和旧Development33385全部保留。

## 2. 做法与证据

设计参考：实际读取 Sim 网站及 block-view/workflow-edge-view/workflow-edge 源码，借鉴紧凑层级、方向端口、选中反馈、Trace/Input/Output和有限事件动画；未复制品牌或源码。Sim浏览器页面两次超时，不声称操作了其登录产品。另核对React Flow、VS Code Sessions、Reap官方资料。

| 原问题 | 本次改进 | 验证 |
|---|---|---|
| 首屏无清楚总览 | 中文九状态、当前节点/轮次/耗时、完成数、汇合依赖、失败与Unknown；设计/冻结运行区分 | projection12、真实顺序/汇合、HTTP竞态 |
| 连线难以理解 | 方向箭头与真实持久交接事件有限脉冲，尊重reduced-motion；数据检查器显示真实字段、来源/目标/轮次/发送时间/接收状态 | 浏览器重连、迟到/逆序与真实交接 |
| 下游请求是大段协议 | 四段实际输入优先、初始化发送标记、写入哈希、CLI回报与实际后端unknown分开；高级身份默认折叠 | 实际运行请求与输入哈希相等 |
| 会话像调试日志 | Provider或Workflow→节点→会话、最近/运行过滤、Markdown回答、工具默认折叠、同一原生身份 | product17、tools12、真实history5会话 |
| 工具结果无法关联 | 显式native call_id匹配、反序结果、原生记录时间差或unknown；冲突清空兼容数据、历史截断提示、可见文本解包后再次脱敏 | 原审核反例、12工具单测、HTTP/Chromium |
| 空白入口与预检不足 | 真正空白初始/新建画布、五步引导、三个可选真实模板、缺项直接定位节点与提示词字段 | 浏览器空白/模板/预检及真实目录选择器 |

最终154文件候选 SHA `164a0cd29d338e0bc9257a8bc7f3eb292befcc7305f10792831c921eb8b032b9`，tree `1797893a1eca77744c59e6b4e86e96c275f689e3`。合同 SHA `cf63c4ee5ef1ecf4a3682cafffa958d90935a6909ace04e9604897ae950ffa85`，run `7e6325c995dc44ac959596695a13a041`。

最终完整自验：473 Python、6宿主隔离、142普通Chromium/HTTP、12projection+6editor；全部exit0，FAIL/ERROR/SKIP=0。baseline、六项语法检查及前端重建exit0，构建产物逐字节一致。测试未删除或改Skip。具体命令/退出/日志哈希见 evidence-summary.json；原始输出在本机 regression/candidate10。

真实模型证据另列：Studio代操作启动顺序 run8f784b29b4fd2facdd1b006d92739f9b（2调用）和汇合run48b6934b3c6288f015b66141bb1c4c26（3调用）；实际Codex gpt-6.1-sol/xhigh、Claude请求deepseek-flash[1m]/high。5调用exit0，原生UUID/HOME/cwd/记录文件及哈希、输入发送哈希、初始化一次、同候选、汇合后下游一次均核对。刷新恢复同run与3调用。实际后端与生效effort未获独立证明，记unknown，不能把CLI配置当实际模型证明。合成测试不冒充真实Agent验收。

## 3. 决策记录

本次用户明确授权完整实施、回归、真实Claude独立审核最多5轮、正常提交/推送一个增量开发PR；禁止自动合并main、升级Stable或删除历史数据。仓库规则已有授权不重复索取。原Issue将新手动作分三阶段，本次明确用户指令要求五个操作，因此合同追加authority_clarification保留五步；原合同和全部8义务不删除、不降低。

改动仅展示、公共工具历史投影及对应测试；源码冻结后禁止继续改动并复用旧ACCEPT。新缺陷必须新候选重验。固定外部监督程序调用未改旧Stable Gate，待审Controller不批准自身。任何必需合同失败、必需finding未闭合、身份不一致或实际进程失败均拒绝正式验收。旧Issue12/PR13审核预算与负面结论不修改。

## 4. 结论与边界

同一最终候选自验、真实顺序/汇合、Claude R2硬ACCEPT及固定旧Gate均通过。源码已提交并推送至cdc53cd0e04ee1e980b229686725a148bf2f432e，远端tree与被审1797893一致；[PR15](https://github.com/Silver-Zhang/DevFlower/pull/15)保持Draft等待用户体验确认，GitHub三项CI均SUCCESS。技术自动化验收不等于用户本人验收或Stable批准。

本机入口：`python3 /home/workspace/DevFlower/.local/open-issue14-workbench.py`，当前Development候选164a0cd2；私有认证网址不入库。原Stable入口open-stable.py和版本5816保留。本轮不授予新Stable批准。

本地Agent实际操作是产品测试，不是用户本人体验验收。30秒识别状态、长对话阅读舒适度及实际视觉偏好仍待用户确认。Provider物理后端/生效effort未知；普通结构化工具数据保留为数据，不推断隐藏思维。会话扫描与历史保留原有预算边界，不在本轮重写执行器。

## 5. 过程记录

| 阶段 | 原始结论与处理 |
|---|---|
| 基线 | 459Python、6host、129浏览器、6editor，均0；真实状态、worktree与Stable已记录 |
| 开发自验 | 保留所有旧代候选、失败与Codex完成核验BLOCKED；依证据修复生命周期列表竞态、文本解包和缺少空白入口，不算Claude源码审核轮次 |
| Claude源码R1 | 候选7f5a7131/tree14fc8f83，原始NEEDS_CORRECTION。7合同PASS，I14-03 FAIL；P1 I14-03-TOOL-TIMING OPEN。P3 HANDOFF-ATTEMPT NOT_REPRODUCED（当前attempt1），未扩展执行语义 |
| R1真实进程 | PID2429906，exit0、387.349秒，session55c5da7d-dbf1-4ba6-859c-e20a518e160e；HOME archives/devflower-issue14-20261024/runtime/r1，cwd /home/workspace/DevFlower。模型请求deepseek-flash[1m]/high，后端/生效effort unknown |
| R1环境限制 | 审核者隔离内Python有4个环境失败（3嵌套隔离、1长UNIX socket路径）；原始失败保留，宿主完整绿不替代审核者结果。R2提示TMPDIR=/tmp |
| 真实候选9风险分析 | Claude产品测试路指出冲突兼容字段、静默截断、混合协议块等。宿主反例证实三项，定向修复并新增4单测；原始负面输出保留native-candidate9。它与预算内正式源码审核分开 |
| 最终候选10 | 154文件164a0cd2/tree1797893，完整473/6/142/18零失败/跳过；真实5调用通过，独立开发完成核验IMPLEMENTED，不是独立ACCEPT |
| Claude源码R2 | 恢复同一项目审核UUID/HOME，完整候选只读、独立scratch；实际PID2623130，请求deepseek-flash[1m]/high。先合同/源码/差异/反例，再开发报告。原始最终ACCEPT，375.662秒、exit0；8/8 PASS，P1 CLOSED；P3仍NOT_REPRODUCED |

| R2独立动态限制 | 沙箱473项中470通过、3项嵌套隔离不可用失败，0ERROR/0SKIP；宿主473/473通过。审核者的3份独立反例脚本在受控宿主原样执行，均exit0。保留非阻断项：未知协议/任意字典包装按结构化数据显示；相同call_id与内容但工具名不同未标冲突 |
| 固定最终Gate与交付 | 未改旧Stable Gate SHA12f0b6aa，实际exit0/ACCEPT；报告哈希e6e5a31552e273174e32e463429cb410b980976b5d722447dbbfe28ac875d6e3。显式19路径提交后tree与候选一致，普通push且GitHub读回HEAD/tree一致；不合并main |

原始大日志、截图、完整裁决、原生JSONL和认证均只留本机 `/home/workspace/DevFlower/archives/devflower-issue14-20261024`。云端研发分支仅保存本任务五节README、必要机器摘要及完整源码清单，不上传原生会话或截图。
