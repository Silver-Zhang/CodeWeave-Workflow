# M1-Final：索引刷新保留与邻接查询实测

## 1. 目标与范围

B模式。修复Refresh indexes重置历史选择、历史选项分页保留及异步刷新竞态；先做失败回归再修复。对neighbors只做实测，只有正常M1可复现性能问题才局部优化。不做M2、main合并/tag/release、私有项目或旧档案改写。

开工CodeWeave feat/m1-interactive-map HEAD2d49db0e0b3d5e17cb95e9b876ffea0077e4ba8b；DevFlower project/codeweave HEADb324efc8d42e6ebb0a7a43cf282ed853e7558b35；remote分别Silver-Zhang/CodeWeave.git与Silver-Zhang/DevFlower.git，staged/unstaged/untracked均为空。已读双方AGENTS、当前入口、上轮任务和三轮真实审核记录。

## 2. 做法与证据

预定义刷新判据：首次空选择可选最新；历史已选在普通刷新/新发布/超出第一页/失败重试下保持index_id、图和源码；手动切换清空；延迟刷新不能覆盖新选择，重叠请求只采纳最新列表；空库清楚报错可重试。组件加真实Clang/SQLite/HTTP/Chromium验证，保留旧版失败日志。

性能判据：自有真实索引加明确合成规模，记录只读DB连接/SQL计数、重复测量分布、节点/调用实例/分页/字节数；覆盖共享少数目标、多目标、环和重复调用。无预设毫秒门槛，不凭单次延迟宣称瓶颈。

原始日志本地`m1-final-hardening-20261019`。先增加8项组件断言，旧版实际7失败/1通过（refresh-before-fix-race-tightened.log，退出1），修正后8/8通过。旧错包括历史被选回latest、第二页选项被清除、延迟请求覆盖other、过期列表obsolete反选。显式切换原本正确，未改变判据。一次包装命令误填不存在可执行文件，没有产生测试结果（refresh-before-fix.log为空），不计失败复现或PASS。

修正仅App索引列表状态与稳定前端文档：首次无选择自动最新；刷新合并已加载历史选项/去重，选择用函数更新保留当前值；独立controller和请求序号拒绝过期响应，卸载abort；列表错误与图/源码错误分离，保留视图并Retry。明确手动切换的原隔离effect不变。没有修改解析、数据库事实或query实现。

正式`bash scripts/verify_m1.sh`全新构建：110后端+fixture unittest1、35前端、7真实Chromium通过，退出0/零Skip（logs/m1-full-final.log/.process.json）；main.cpp SHA25623ada77249c036cbacf2a21ddc6664601741f77d1d4cdb4d32cc85c817a2842b，新binary8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94。首轮6/7浏览器通过，一条新增测试的泛用role=alert匹配到Monaco内置多个alert，修正为索引sidebar错误区、功能断言不变后全量重跑；原始失败及trace单独保留在logs/m1-full-first*。

补充Node/Chromium矩阵：公开CLI实际生成22个双TU索引，包含超出第一页的历史选择；再实际发布2个新索引，验证选择/图/调用点及Monaco原文与旧API快照相等。延迟原HTTP、重叠请求（原响应字节不改）、用户显式切换清空并重新查询、503注入/真实重试、真实空schema首次报错后CLI发布首索引/重试自动选择，共6组PASS，退出0；browser-matrix/result.json、indexing.json和logs/browser-matrix*.log。除了明确时序/503注入，其余事实均来自真实SQLite/Clang，未伪造成功数据。

完整62文件候选清单SHA256 `f0714eb0def67f241fc14a442465202fcbf170e5e224e6bd32837a8d7795998c`，见[candidate-manifest.json](candidate-manifest.json)，包含新增两份回归测试。审核时HEAD为2d49db0e，4个本轮改动未提交；复制前后及结束原/审核副本bytes/mode一致。最终结果commit `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`，tree `ffabf3d59a334349126ae2fec9923660d844e597`，62文件Git tree逐字节/mode与接受清单相等，源工作区干净；指定远端同SHA，push exit0。

### 邻接性能实测

本机Intel i9-14900K/32逻辑CPU、Linux7.0.0-38 x86_64、Python3.12.3、SQLite3.45.1。3次warmup+31次未打桩暖缓存计时；另一次打桩单独统计persistent连接/SQL与每次schema验证的memory连接/SQL，不把内存建schema当成持久库写入。SQL计数包括PRAGMA、schema元数据校验和事实SELECT，不只统计业务SELECT；P95采用排序floor(0.95*(n-1))的lower经验分位。真实多文件数据由本轮新analyzer/公共CLI/Bubblewrap生成；其余明确为合成SQLite规模行，不能证明Clang语义或大工程冷缓存性能。

| 数据/limit | 节点/调用点 | 持久连接/SQL | memory连接/SQL | 中位数 / P95 ms |
|---|---|---|---|---|
| 少量4实体3调用 /12 | 4/3 | 6/39 | 6/72 | 2.395 / 2.448 |
| 120调用共享2目标 /50 | 3/50（有剩余） | 5/80 | 5/60 | 2.403 / 2.462 |
| fanout1 /50 | 2/1 | 4/25 | 4/48 | 1.583 / 1.619 |
| fanout12 /50 | 13/12 | 15/102 | 15/180 | 5.773 / 5.903 |
| fanout50 /50 | 51/50 | 53/368 | 53/636 | 20.224 / 20.410 |
| 环/重复160调用 /50 | 3/100（双向有剩余） | 5/130 | 5/60 | 2.838 / 2.874 |
| 10002实体/50200调用/16.82MB库 /50 | 51/100（双向有剩余） | 53/418 | 53/636 | 21.102 / 21.264 |
| 同规模、界面limit12 | 13/24（双向有剩余） | 15/114 | 15/180 | 6.206 / 6.448 |
| 真实双TU17实体18调用 /12 | 4/4 | 6/40 | 6/72 | 2.480 / 2.536 |

完整规模/分页/字节/计数摘要见[performance-summary.json](performance-summary.json)，原始31次样本在本地performance/results.json；[measure_neighbors.py](measure_neighbors.py)可重现，运行方式：`PYTHONPATH=<CodeWeave>/backend <venv-python> measure_neighbors.py --source-root <CodeWeave> --work <新独立目录> --analyzer <新构建binary> --resource-dir <lib/clang/18>`。每组同样数据重复结果相等，调用实例/分页与种子预设oracle相等；所有持久连接URI强制mode=ro、authorizer无写尝试、库SHA256不变。最大正常响应45742 JSON字节，极端单实体150KB anchors组成的超大图明确query_limit，库不变。

**确认N+1（不同邻居增加引起连接/SQL线性增长），尚无正常M1使用受阻的实测证据，因此本轮不优化、不宣称已消除N+1。** 保留未来局部批量查询建议，不能泛化这些暖缓存毫秒数据到大型真实工程。

### 本轮Claude独立复核

同一原UUID06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6、Opus5.5/xhigh/auto，完整62文件本轮**唯一正式裁决ACCEPT**；[原报告](review/report.md)、[机器结果](review/result.json)、[自主检查表](review/checklist.md)原样归档，不改写。刷新P2独立CLOSED，findings为空。实际新构建完整110/35/7+fixture1，7样本性能复测，真实22历史索引+另1索引/HTTP/Chromium反例PASS，前后62文件hash/mode一致。

这是一个固定候选的一轮完整审核，中途三次print启动：首次由监督者暂停澄清反复的harness/环境前提；第二次随交互回合中断而终止（退出码未捕获）；第三次完成并实际输出结构化ACCEPT。前两次无正式裁决，没有被改写为通过：attempt-1中CLI虽exit0但result.is_error=true/aborted_streaming，无structured verdict；attempt-2的原PID和exec session已消失且无报告。所有原始输出留本地round-1/attempt-1、attempt-2及最终round-1，次数不伪装为三轮完整审核。

审核脚本的错误不是生产缺陷：先用2索引fixture等待不存在/禁用的older按钮并在清理触发route错误；随后误期望主动切换保留旧source（与用户合同相反），改为先确认清空、显式点符号重新加载；最后把原生option的存在错当可见，改用attached后完整通过。失败的Read路径/Python路径/work目录预创建、auto拒绝递归清理均保留；测试后来用新目录，未关闭auto保护。CodeWeave源码和旧任务未被审核者改写。

证据范围核对（Codex）：Claude的第23次CLI发布实际早于页面首次加载，其自有脚本证明“有较新已发布索引时，第二页历史选择/刷新及改选后重新定位保持正确”，不将它冒称“浏览中才发布新版本”的独立运行。后者及超出第一页刷新后的源文逐字比较由本轮Codex browser-matrix真实执行；角色分开。原Claude报告的简写保留不改，精确支持范围以脚本/原始结果为准。手动切换要求清空，刷新同一index才要求保留，二者不混淆。

Claude独立性能复测使用同一已审方法，7次样本：UI limit12持久15连接/114 SQL、中位约6.144ms，moderate limit50为53连接/418 SQL、约21.080ms。所有只读/页数/实例/字节/DB hash检查通过；不是第二套查询优化，也不代表生产/冷缓存规模保证。

## 3. 决策记录

用户本轮附件明确授权定向实施/测试/Claude闭环，只有同完整候选Codex全验+真实Claude ACCEPT+身份不变+隐私/许可证/远端检查通过才自动提交推送两个指定分支。原CodeWeave独立审核会话06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6，Opus5.5/xhigh/auto；需每轮重新审完整候选，最多5轮，不把历史ACCEPT用于新版本。

变更卡：风险为列表分页、React异步状态及旧索引串用；保持解析事实/schema、图预算与索引切换隔离；先测试旧错，再小幅修正，随测量决定是否需要查询优化。回退须另行保留已有工作，不reset/clean。

## 4. 结论与边界

**本轮实施、Codex最终自验及Claude真实独立复核完成；唯一正式裁决ACCEPT，无未关闭P0/P1或必需P2。** 同一62文件候选未变，ACCEPT后完整新构建110/35/7+fixture1再次通过，零Skip。源码结果commit `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`已正常推送至`origin/feat/m1-interactive-map`并核对远端精确SHA；用户授权的是指定分支Git交付，未合并main、tag、release或M2。

DevFlower本任务和必要导航随`project/codeweave`归档，工作流最终SHA与两个远端实测结果见本轮交付回复及本地`m1-final-hardening-20261019/delivery.json`，避免把工作流SHA混作源码身份。任务“已完成”表示研发、自验、独立复核与归档完成，**不代表用户正式验收或冻结**。

建议用户进行最终使用验收后批准M1冻结。保留N+1与本机warm-cache证据边界；不以当前数据保证大型真实工程、冷缓存或跨平台性能。

## 5. 过程记录

| 日期 | 实际事件 |
|---|---|
| 2026-10-19 | 双仓干净基线，B立项；核实当前Claude CLI2.1.303认证有效，读取上轮原会话参数及原始负面/关闭结论。 |
| 2026-10-19 | 测试先复现旧版7失败/1通过，再定向修正；首轮浏览器locator问题保留，修正测试定位后完整110/35/7+fixture1通过。真实22索引矩阵6组通过；确认N+1但当前正常场景无阻塞证据，不优化。固定62文件f0714e候选，以原UUID/Opus5.5/xhigh/auto真实启动本轮第1轮复核。 |
| 2026-10-19 | 同候选一轮真实审核经两次中断恢复，最终新构建/110后端35前端7Chromium/fixture1、独立22真实索引变体、独立性能7样本和结束62文件核验通过，结构化ACCEPT。所有无裁决或harness失败保留，精确证据范围及执行者分开；开始最终交付关口。 |
| 2026-10-19 | 正式ACCEPT后最终新构建verify_m1.sh于08:22:24–08:23:06 UTC实际exit0，110/35/7+fixture1、零Skip；logs/final-after-accept*。62文件与接受清单仍一致，依赖锁未改、production audit0、许可证无缺项、定向隐私/构建物检查0；远端仍2d49db0e/b324efc8。按用户既有条件授权执行明确文件Git交付。 |
| 2026-10-19 | 仅4个明确源码路径暂存并提交6c3d1b8，提交前index tree和提交后HEAD tree均62/62与f0714e接受字节/mode一致。源码正常push exit0，远端精确SHA相等，工作区干净。仅当前任务与必要导航归档；最终工作流提交及双远端核验见交付回复/Git ref和本地delivery.json。 |
