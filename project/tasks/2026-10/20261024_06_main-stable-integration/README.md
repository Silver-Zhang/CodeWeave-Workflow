# main整合、分支收尾与人工固定版本启用

任务：20261024_06_main-stable-integration。任务完成指用户授权的人工集成、记录同步和固定版部署；不等于旧整版验收合同或原技术Gate已通过。

## 1. 目标与范围

用户明确要求：main成为最终最新源码，所有开放PR合并，长期保留main和project分支，清理其他分支，并更新Stable。起点main为e35dec1，开放PR15/17；源码已完成两个P1修复，原始独立审核和最终Gate因真实正向流程缺口仍BLOCKED。开始前已检查源码全部干净、项目记录干净，未覆盖用户修改。

范围为正常Merge Commit、分支治理、本机固定安装/入口和记录。不扩展产品功能，不覆盖原Stable安装/认证/会话，不重写原审核，不自动批准未来任务交付。

## 2. 做法与证据

先保存用户原话、已披露限制和操作边界至本地owner-authorization.json，完整Git refs bundle经verify通过。先给PR追加所有者人工决定说明，保留全部原始负面报告，再按依赖顺序集成。

PR15以HEAD546cba4正常合并，merge commit ee0a49384b2fbfd5feee9654ef8289733ead9be5。将新main普通merge到PR17形成27864fcfd6b24fa374f9bbc89fb8cc680f32fa96，确认Git tree和175个源码文件与最终4eb候选完全相同；PR17改base为main，三项新CI全部成功后正常合并。最终main为bedee3229e0c4420c9112a5b62eac9a0e81d6458，tree2e3c444f036e6f2e02bfcddd8301a5f0b1cd8e79，完整CF7b0c0b3bcc95235e02eadb74b71dd5f50d3d9c88da178b4787ff2090d1978210。

干净本地main实际fetch/pull --ff-only后核对tree。再次确认无开放PR、两个head均在main历史中，detach原工作树保留文件与会话路径，删除最后两个本地/远端开发分支。现在本地只剩main 和 project/devflower，云端另保留project/codeweave。原工作树未删除。

本轮真实重跑：547 Python、6host、165普通Chromium/HTTP、20JS，均exit0、FAIL/ERROR/SKIP0，baseline与6项语法通过。实际测试HEAD为27864fc，与最终main及固定安装的完整文件清单、tree、CF完全一致。合并后又在main执行baseline和6host，均通过。原始命令/日志/计数留本地regression/integration；必要摘要见integration.json。不把合成浏览器测试当新真实模型验收，本轮没有新模型调用或审核轮次。

固定175文件安装到stable/main-7b0c0b3bcc95；原Stable5816完整源码哈希不变。新日常工作台使用固定源码、当前批准Profile、同一storage/native目录；停旧服务前确认唯一run为FAILED、对话操作均COMPLETED且无PTY，对SQLite作一致性本地备份，仅停止明确记录的旧服务PID，再启动新服务，未移动或复制原生HOME。

统一启动器open-devflower.py及三个兼容入口，旧脚本原文保留。实际HTTP200和候选身份检查成功，经HTTP打开main工作区；明确不是GUI/用户本人验收。保留2个工作区、1个历史失败运行及原生历史关联。实际工作台仍返回stable_approved=false，外部交付配置为空。

records通过普通merge接收main，并把project.json的framework_base更新为实际main。当前[使用指南](使用指南.md)取代任务05安装说明，旧任务及其当时结论均不修改。

## 3. 决策记录

用户在上一轮已获知BLOCKED及Claude300秒超时后明确表示：“我的意思是main分支就是最终开发版本了，把所有的PR都合并了，最终状态就是main就是最新的，然后project分支，其他的分支就整理或者清除解决。stable我认为可以更新了”。本轮按该人工决定集成，不再把此前的条件式合并授权误作本次明确指令。

人的集成/使用决定与模型审核、运行Gate分别记录。没有把所有者批准写成Claude硬ACCEPT，也没有伪造TrustedRelease要求的ACCEPT回执或修改Controller门禁。v3没有正式可信Stable启用路径，因此只将main固定副本与默认日常入口切换到用户批准版本，真实技术信任标记仍false，原可信Stable链保持不变。

风险包括未完成真实全流程证据、原生会话路径依赖和并发数据库写入。采用Git备份、正常merge、精确HEAD匹配、CI读回、部署前静态状态核验/SQLite备份、单服务租约和原路径保留降低风险。没有force/reset/clean，不删除project分支和旧安装。

## 4. 结论与边界

PR15/17均MERGED，main为最新完整工作台；本地main已同步。开发分支已清理，records采用最新main，原研发记录和日志保留。日常固定版已启动，唯一推荐命令：python3 /home/workspace/DevFlower/.local/open-devflower.py。

本轮是人工决策后的集成，不是旧合同技术验收完成。原Claude R2 BLOCKED及Gate exit2/BLOCKED继续有效；两个P1 CLOSED，但真实顺序Claude超时与汇合未补证的缺口未消失。没有新独立审核、没有宣称用户亲自UX验收。

Stable目录已有新main固定副本，默认入口已切换；v3界面仍标Development，可信Stable标记仍false。正式TrustedRelease晋升没有执行，因为现有v3入口不支持且缺独立硬ACCEPT，不能通过造批准文件来完成。原可信Stable5816及全部历史安装保留；旧启动配置漂移没有被偷偷重签。

任何未来自动交付仍受当次授权与原Gate限制。当前默认服务没有配置自动GitHub交付节点。用户可使用会话和画布，不能把这次人工合并当成所有后续任务的永久许可。提交/推送与远端读回结果由本地收尾回执记录。

## 5. 过程记录

| 时间（北京时间） | 事件、失败及纠正 |
|---|---|
| 2026-10-24 | 核验真实PR/CI及所有工作树；记录新人工集成指令，保存refs备份。 |
| 2026-10-24 23:03 | PR15普通Merge Commit成功，读回ee0a493。 |
| 2026-10-24 23:04 | PR17普通集成新main，树和完整源码不变，更新base并等待新CI。 |
| 2026-10-24 23:07 | 三项CI成功；PR17正常合并，main读回bedee322，干净本地ff-only更新。 |
| 2026-10-24 | 删除两个已合并开发分支；项目档案普通merge接收main。 |
| 2026-10-24 | 完整回归全部通过，保留实际测试head和最终main同tree/CF的核验。一次浏览器计数汇总脚本误按dict读取list，修正汇总后实数165；未改测试结果。 |
| 2026-10-24 | 新固定版实际启动、保留原数据库和HOME、HTTP打开main；入口保留真实未晋升标记。 |
| 2026-10-24 | 更新指南/任务/导航并同步项目档案；原始模型负面裁决保持不变。 |
