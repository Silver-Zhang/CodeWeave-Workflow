# 统一 Agent 工作台与可执行画布——完整产品升级

## 1. 目标与范围
执行2026-10-21完整产品任务卡，继续flow/agent-workspace-vnext / Draft PR #10。实现目录窗口、命名原生会话、React Flow可执行画布、通用Agent、初始化与交接、顺序/只读并发/条件/有界循环、可信验证和受控交付。任务身份a026ef48f030c5725d7f6cfab7951e71。用户2026-10-22批准继续开发并指定Claude Opus 5-5 1M/high。旧Issue9运行和有限接受保持原意，不能批准新候选。

## 2. 做法与证据
当前完整候选`e194382a7e84b309d7d91034a5d093dee1daa10b6bda69b74be954b943bf8f3c`，130文件，预期Git tree `84070e9471b27e27135ec05df39e61764473e403`；源码HEAD与origin仍465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0，main仍61356ac07aca24382970b72de9607b1daff26767，未提交/推送本次源码。自验绑定本机regression/candidate-8：381 Python、6宿主隔离、7套普通Chromium/真实HTTP共113检查全部通过，失败/错误/Skip均0；baseline、6项语法及diff --check退出0。浏览器回归使用合成原生数据，不冒充模型验收。

预算WB-UI-01先复现24≠10，修复为冻结运行根预算并禁用编辑。另复现慢响应持续丢弃导致监控不更新，改为单个在途查询、5秒可取消超时和当前运行身份核验；新增慢查询与挂起查询负例。真实Codex修复过8个限定文件：只扫描原生错误信封，超时/溢出优先；任务卡精确UTF-8哈希绑定验证/交付桥接。44会话+55工作台针对测试通过，原始13失败保留。该开发/局部Claude审核使用中间dfc候选，不冒充最终完整接受。

最终候选真实模型核验：run 13fc637d6ae3d3fac1388365aa8b5594共6次实际调用，Codex循环与Claude只读分支进程重叠57.191秒、汇合2/2、汇总只运行一次，后接真实Claude审核及Agent权限探测。所有输入源码均为当前候选、进程退出0；循环UUID不变，初始化[true,false]，暂停恢复成功。实际Ask/Plan写入被拒绝，Agent只写自有测试文件，Git及父目录哨兵未变，测试文件核对后移除、源码恢复原哈希。

自建真实会话改名、分叉、原生归档/查看/恢复、回收站/恢复完成；新run 99f1293ffdb7b229914719324c88baed恢复准确UUID/HOME/cwd并重新初始化一次，实际停止后进程组/worker均退出、原生记录保留、下游未执行、拒绝恢复。真实RPC归档后人为丢回执，事务RECOVERY_REQUIRED且第二次操作拒绝，未重复发RPC。最初外部测试读错SQLite库的失败保留，补充从正确事务库读回，不重做原生副作用。run cabd7871c763506d946e7d9d8cd8dc5b实际5次Codex同UUID/初始化一次后达到上限，原状态FAILED是预期负例，未伪称完成；浏览器实际刷新未重复启动。

固定旧Stable实际验证：run 6f8e55210a4c4c709f2b9f7c15495b13使用既有批准8e83d127…；真实Codex复制130文件并核对，旧Stable执行1条父断言核验当前381测试及命令的实际日志、哈希、数量。随后Studio→固定桥接→旧Stable核验4例：匹配成功，缺grant/错任务哈希/失败测试+诱饵ACCEPT均失败；0模型调用、未交付、未批准新Stable。本地bare测试覆盖成功push丢回执、远端竞争和双库部分交付，合成裁决仅测机械故障，不批准真实产品源码。

补齐R4两项证据：实际CUA在当前Chromium工作台对自建真实Codex/Claude会话搜索、保存别名、刷新并分别从原节点打开同一会话；句柄/UUID与实际两轮请求一致，原生可见历史及工具活动未变。Claude原生结构化回答按工具活动折叠，在实际节点结果中呈现；没有伪造普通聊天气泡。截图、HTTP读回及执行者分别记录。

真实修复run 4f4b0982aefcc4530edfb1f7f5155f01：完整当前DevFlower自有clone中，仅新增fixture子目录可写。4个实际CLI步骤分别为Codex建立明确的历史竞态复现、Claude独立指出3类缺陷、Codex仅修复budget_display.py并运行8组实际回归、Claude只读复审。因其工具无进程执行，最初accepted=false；固定外部runner另在断网只读bwrap中实跑相同5个反例测试，seed出现10个失败，fixed全部通过。准确原Claude会话先保留身份未绑定的否定报告（将文件SHA与目录清单SHA误比对）；新增逐文件清单、明确3层身份后，独立局部复审29ca457d…给出accepted=true/先前缺陷CLOSED，仅限该fixture，不是完整源码或交付批准。真实执行者、旧false报告和错误引用被标不可访问的原始结果保留，正式源码始终e194未变。

所有原始日志、请求、截图、原生记录、冻结候选及失败保留于本机archives/devflower-workbench-20261021；机器摘要见evidence.json。没有上传原生会话、隐藏推理或凭据。

## 3. 决策记录
v3另存、不迁移旧授权；采用React Flow并复用原生CLI索引、固定进程监督和隔离。Ask/Plan强制只读，同源码写入互斥；Agent不能写权威状态或Git凭据。解释器/脚本/配置/依赖树全部固定，外部grant仅由独立固定程序提供。候选Controller不得审批自身，源码公开必须由固定旧方式复核；生产交付不能借用只验证且commit/push=false的Stable测试授权。

独立源码审核最多5轮：R1 DeepSeek真实503无裁决；R2 Opus首次外层进程中断，准确会话恢复后超时，无原生裁决；R3原始和最终均BLOCKED，必需项R3-002要求同最终候选真实并发/会话/权限/停止/Stable验证。R3安全Python与3条独立反例通过，但缺证据仍阻塞。所有负面报告原样保留。R4首次达到1200秒监督时限，无stdout裁决；确认进程退出后准确会话恢复一次，独立与最终原始结论均BLOCKED。A、C–J、L通过；必需R4-B要求两类真实会话GUI证据，R4-K要求实际开发—发现缺陷—修复—复审，未把分析/权限探测冒充修复。R5同一源码独立原始裁决BLOCKED（exit0/645.469秒）：原R4-B与R4-K均CLOSED，A–J及L为PASS，但完整产品合同K仍BLOCKED。其结论明确区分限定fixture闭环与完整产品验收，未批准整体发布；未给出新的具体OPEN finding。摘要对照300秒超时，一次准确同会话恢复480秒再超时，均exit-15/无stdout，无最终原生裁决。保留原BLOCKED和所有超时，不伪造完整ACCEPT。5轮已用尽，停止新源码审核。

Claude请求/CLI回报模型claude-opus-5-5[1m]，effort请求high，实际resolved effort及中转站物理模型unknown。明确审核会话3e8c1139-9c48-4aab-ba55-ce848ebd1653，持久HOME为本任务runtime/reviewer-round-2，cwd为/home/workspace/DevFlower，原生记录在该HOME的.claude/projects/-home-workspace-DevFlower；不覆盖用户全局认证，不用--last猜会话。

## 4. 结论与边界
当前BLOCKED，不声称完整产品验收、READY_TO_MERGE、用户验收或Stable晋升。预算、监控、桥接及取消修复已实现并通过自验，但第5轮原始整体结论仍BLOCKED，最终对照不完整；5轮预算已尽，不继续尝试取得ACCEPT。当前源候选未commit/push，PR #10仍Draft/旧465内容。研发记录单独同步project/devflower，源码只到flow/agent-workspace-vnext，不合并main，不改CodeWeave/RMC，不删除原生会话。本次源码不提交/推送。只同步本project分支的研发记录和PR状态说明；后续完整产品K的实际任务与独立验收仍待处理，不能借旧有限接受或局部fixture接受发布。两分支分别记录，不宣称原子交付。

本机入口：`python3 /home/workspace/DevFlower/.local/open-workbench.py`，当前Development http://127.0.0.1:42033/（入口自动本机认证，私有URL不公开）；操作指南docs/WORKBENCH.md。旧Stable不覆盖。Copilot仅ACP初始化/空会话探测，实际推理仍禁用；无用户最终可用性验收，不扩展终端CLI下一阶段。

## 5. 过程记录
2026-10-21：核验工作树与权限，建立新完整产品任务，实施v3及React Flow；实际开发修复、原生操作、并发与循环验证。363+6+110自验通过，Claude503按停止规则保留BLOCKED。
2026-10-22：按最新指示继续，Opus通道真实探测成功；关闭预算错显，完成固定桥接和原生停止；真实Codex继续修复错误分类及合同哈希。R2中断/恢复超时、R3缺动态证据BLOCKED均保留。新增慢查询修复后381+6+113通过，补齐当前候选真实矩阵、生命周期、五轮上限及旧Stable验证；R4 BLOCKED后按原意见补真实双Provider会话GUI与限定修复闭环，启动最终R5。未自动合并、未晋升Stable。

最终停止记录：R5原始已确认本轮实际双会话GUI与真实限定修复闭环补证有效，并独立重跑5个fixture反例通过；其完整合同K仍BLOCKED，未取得硬ACCEPT。最后摘要对照及准确恢复均超时，无新最终裁决。保留当前e194/84070候选、原生记录和所有失败；源码HEAD仍465，不发布本轮实现。研发记录正常同步与PR状态更新以delivery.json及最终报告的远端读回为准。

七项诉求按可验证边界列示：目录/整体布局、节点配置、初始化、交接、图调度、启动监控均已实现并有上述测试；会话中心在支持的managed Codex/Claude范围完成真实GUI及生命周期验证。完整产品任务验收/PR交付仍未完成；Copilot仅能力/空会话探测，实际推理禁用；Claude原生结构化结果在工具活动折叠及节点结果查看，未冒充普通原生文本。所有实现、自验、局部复核与整体BLOCKED分别陈述。
