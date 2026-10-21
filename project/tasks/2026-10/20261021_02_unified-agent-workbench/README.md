# 统一 Agent 工作台与可执行画布——完整产品升级

## 1. 目标与范围
执行2026-10-21新产品任务卡：目录窗口、命名会话、React Flow可执行画布、通用Agent、初始化协议、可见交接、顺序/只读并发汇合/条件/有界循环及真实开发审核交付。继续flow/agent-workspace-vnext / Draft PR #10；新任务运行a026ef48f030c5725d7f6cfab7951e71。旧Issue9运行及其BLOCKED、有限接受和五轮预算保持原状，不作为本次独立审核。

## 2. 做法与证据
源码HEAD仍465a31f523fc265b1bcbcd0ecdef6eca06a6e0e0，最新origin/main仍61356ac07aca24382970b72de9607b1daff26767。本地完整未提交候选b1b2cfdf90a16e6347566f2e9123afb5648a46b785effa1dc59ce7e84aab1e11，127文件，预期Git tree d7528dd0915895ddd1c121e50cf81c40b3518b5e；不是HEAD tree，也尚未提交。

当前候选完整自验：363 Python测试、6宿主隔离测试，失败/错误/Skip均0；check --baseline及6项JS语法检查退出0。7个普通Chromium/真实HTTP套件共110项检查（其中会话套件32条断言），均退出0，不冒充模型验收。新增协议/调度/存储/HTTP测试40项包含在363内。附加git diff --check退出2：THIRD_PARTY_LICENSES.txt末尾多一空行，格式项待整理，未记为通过。早期真实失败和测试脚本错误保留，最终通过不覆盖原记录。

真实Codex gpt-6.1-sol/xhigh完成21个回合：顺序2、实际源码修复1、并发汇合3、两轮循环4、五轮上限10、旧会话新运行1。两只读进程重叠81.774秒，汇合2/2且汇总只执行一次；两轮提前结束，五轮负例原始状态FAILED/10调用/达到上限，未伪称成功。同一节点跨轮UUID不变、初始化首次true随后false；新运行精确恢复原UUID并重新初始化一次。暂停/刷新/继续未重复启动。模型及effort无resolved字段时均记unknown。

自建Codex原生改名、分叉、归档/查看归档历史/取消归档和DevFlower回收站/恢复实际成功；原生终端按原HOME/cwd/UUID及同HOME锁实际打开后退出，未发送新消息。仅操作本任务自建会话。真实Claude既有历史已在GUI读取；Copilot ACP初始化及空会话成功，但模型目录/推理未验证，执行仍禁用。

原始日志、截图、冻结完整清单、请求、原生记录、故障回执仅在本机archives/devflower-workbench-20261021；入库仅本README、任务元数据及evidence.json。各真实运行绑定自己的源码版本，不把中间版本演示等同最终候选独立ACCEPT。

## 3. 决策记录
采用React Flow，复用既有CLI隔离、原生索引、监督和旧v1/v2读取；v3另存，不迁移旧授权。Ask/Plan强制只读、同源码写入串行、Git元数据只读；请求/事件/状态持久化；结果丢失先核验回执，不能盲重发。候选Controller不审批自身，由固定外部监督组织源码冻结与Claude审查。未覆盖Stable、不改全局认证、CodeWeave或RMC。

Codex实际源码分析找到嵌套循环激活缺少祖先轮次；先新增失败负例，再由画布真实可写节点修复，核对仅修改授权两个文件。另修复原生严格schema400、分叉后不同UUID误拒、原生扁平归档读取、缺失输入汇合、跨端口认证Cookie、配置面板裁切和循环状态显示。旧条件测试改用结果节点收敛互斥分支，另加断言要求默认全部输入汇合拒绝缺项；未删除旧回归或降低合同。

Claude保持deepseek-flash[1m]/high。第一次真实分析失败503；随后固定本候选启动一次独立源码审核，PID3594968，session140b1101-df30-4b88-a8cc-6547cdb865d1，退出1/192.866秒/未超时，再次返回“503 分组 default 下模型 deepseek-flash 无可用渠道（distributor）”。实际resolved model/effort均unknown。没有源码裁决或ACCEPT；BLOCKED是外部监督状态，不能署名为Claude的源码结论。审核启动脚本的前置语法错误另保留，未伪装成一次模型审核。两次服务失败后停止继续请求。

## 4. 结论与边界
任务BLOCKED，未满足完整A–L，PR #10仍Draft，未达到READY_TO_MERGE。本轮源码未commit/push；旧远端465a31f及原有限接受内容保持不变。研发记录单独整理，同步状态以最终交付记录为准，不合并main。

未关闭：WB-UI-01，冻结运行高级面板预算仍读取下一次草稿（显示24，真实冻结预算10并正确执行）；需修复并回归。WB-EXT-01，验证/交付节点目前只有受控适配接口与负例测试，本机尚无可信实际外部程序配置，不能声称研发PR交付已跑通。真实v3原生取消场景未补齐；已有宿主/HTTP测试不能替代。Claude不可用导致真实跨Provider分析、开发—Claude修复复审及新候选独立审核未完成。Provider能力在界面的清晰展示和冻结视图体验仍需后续复核。没有借用旧ACCEPT、伪造人工验收或签发Stable。

本机推荐入口：python3 /home/workspace/DevFlower/.local/open-workbench.py；当前产品http://127.0.0.1:42571/，Development候选b1b2cfdf90a1。入口在本机完成能力登录，不公开私有URL。操作指南在本地源码docs/WORKBENCH.md。旧34235/33915 Stable及41053旧会话预览保留，新入口不替换它们。服务恢复后继续本任务的缺项修复和新候选审核，不能将当前自验当作发布批准。

## 5. 过程记录
2026-10-21：核验仓库、三个干净worktree、旧服务/流程和CLI；建立新任务/合同/运行；阅读官方接口、Reap实际源码与许可证，建立v3和React Flow实现。
2026-10-21至22：保留Claude503、Codex schema400及各轮真实负例；实际GUI驱动分析、开发修复、并发与循环；宿主和Chromium反复验证每次有实质修改的候选；最终363+6+110通过。真实源码审核再次遇503，按停止条件BLOCKED；保存21个成功Codex回合、各候选和原始服务失败，整理记录及Draft状态。用户未作本版最终验收，未自动合并或晋升。
