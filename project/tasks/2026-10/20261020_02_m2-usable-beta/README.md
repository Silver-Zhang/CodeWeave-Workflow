# M2-A：直接交付本地可用版

## 1. 目标与范围

B模式。按已批准M2-R0设计连续实现A1–A6：配置可信本地C++项目和真实编译数据库→启动函数/调用地图与保存源码→编辑保存→网页或CLI手动全量刷新→显示真实请求/阶段/失败→保留旧快照→双版本函数、关系和源码Diff。接口或报告单独完成不算交付。

初始两仓库工作区均干净。CodeWeave origin=`Silver-Zhang/CodeWeave.git`，实查main已含M0/M1，基线`95620d8da6afb8470d78400468fc4eee120147f2`，从它创建`feat/m2-usable-beta`。DevFlower origin=`Silver-Zhang/DevFlower.git`，`project/codeweave`基线`4ae77c6a351cf9430f79bc10dd75f421ab37a227`。不修改DevFlower通用框架或旧任务结论。

用户授权实施、自验、独立审核和必要修正；只有当前完整候选真实独立ACCEPT、自验通过、暂存树匹配、远端无冲突后，才提交推送源码分支并建PR、归档推送工作流。用户暂停更换中转站后，明确改用DeepSeek Flash/max，并另外授权将固定84文件及必要材料发送api.deepseek.com执行限定审核。沿用原CodeWeave独立审核会话，不冒称Opus。不得自动合并、tag、release或进入M2-B。

## 2. 做法与证据

产品代码及稳定文档只在CodeWeave：protocol3定义/调用字节与token锚点；schema4完整快照/workspace/attempt元数据；descriptor封存输入、冻结标准头/ELF最小沙箱；全量刷新/取消/重启/CAS原子发布；raw Git HEAD与明确基线配置；保守结构Diff；共享CLI/HTTP、React Flow/Monaco双侧源码；本地启动器和真实多TU演示。工作流不是运行依赖。

本轮环境：Python3.12.3、LLVM18.1.3、Bubblewrap0.9.0、Node22.23.3和真实Chromium。使用已安装匹配版本，没有安装系统包或改变全局编译器/代理。

```bash
# CodeWeave源码根目录；显式选用已安装Python/LLVM/Node
PYTHON=/path/to/venv/bin/python CODEWEAVE_LLVM_PREFIX=/path/to/llvm18 bash scripts/verify_m2.sh
./scripts/run_local.sh --demo --state-dir /path/to/owned/demo-state
# http://127.0.0.1:8000
```

| 证据层 | 当前修正候选的实际结果 |
|---|---|
| Codex完整门禁 | `full-correction.log`退出0；全新构建分析器；136后端、fixture1、38前端、M1 Chromium7+M2 Chromium2，必需项零Skip。原始构建/测试位于`/tmp/codeweave-m2-acceptance-chSR1a`。 |
| 公共CLI/HTTP与启动器 | 真多TU/vector工程建库；literal7→9及alpha→beta、HEAD比较、旧源、重启复用通过。修正版真实启动入口已重启且保留原状态；7个只读API核验及真实浏览器地图/源码SHA显示通过，无pageerror。 |
| 第2轮独立完整门禁 | 审核者自己的新副本、新构建实际执行`verify_m2.sh`通过，证据`/tmp/codeweave-m2-acceptance-yZE9QA`；另完成六TU、V2–V9、损坏库CLI/HTTP、真实自写Chromium反例。原生最终正常退出并给出ACCEPT，不从脚本退出0推导裁决。 |
| 身份 | 当前完整84文件，无删除；清单SHA256 **40328a84bf1e27948e17d1916ebfd3489a2bc3c4fadadc4560e889703c4a7c95**。原件/规范副本复制前后、Codex门禁后逐文件字节/Git mode/状态一致；规范副本只读、禁pycache。 |

验收合同对照如下；这里是实施者证据，独立判定以正式报告为准。

| 合同 | 真实覆盖 |
|---|---|
| 01–03 | literal/唯一调用目标/双侧源码、只移行与闭包/局部类稳定身份；Chromium完整编辑刷新比较。 |
| 04–06 | 多TU、共享头internal/external inline、简单template、普通/静态/虚方法；宏及constexpr/enum头变化、无关TU不标记。 |
| 07–08、22 | 新增/重命名/删除、uncovered、stale ccdb、scope移除与definition_removed、关系out_of_scope；重复/逆序不重复，冲突配置拒绝。 |
| 09 | 真Git HEAD/staged/保存磁盘不同、生成头、私有无配置stub；历史缺输入仅HEAD失败，不改原Git index。 |
| 10 | cpp/共享头/宏头/ccdb复制时变化只重试一次；seal后宿主变化不混入AST；封存额外篡改失败。 |
| 11–12 | driver/frontend/缺头/响应文件错误与warning追溯；取消、事务故障、commit前后SIGKILL、重启interrupted，旧索引/源保留。 |
| 13–15 | static/重载/跨TU观察、宏双调用/lambda/虚限定/未知指针/取地址；Unicode/CRLF定位及异步导航。 |
| 16–17 | vector/cstddef、受信aliases、物理#line、外部source拒绝、symlink/FIFO/unsafe argv；Git hooks/fsmonitor不是产品执行；optional头及mtime恢复仍重析。 |
| 18–19 | schema3新路径迁移且旧字节不改；缺/损坏/不兼容库；300事件limit1、300unit分页、UTF8长字段/诊断分块预算及完整集合哈希。 |
| 20 | 默认只读、显式可信刷新、Host/Origin/Token/JSON白名单/CAS/busy/idempotency；worker真发布；历史选择及异步隔离。 |
| 21 | M2-B增量复用/加速断言明确非本轮范围。 |

源码分析器本轮新构建SHA256=`b91b17afe37928da6f5f40374f20ee20e4f23f4d2505dfc417925e4e3c9b18b4`。大量日志、截图、受控fixtures和进程记录留本地`m2-usable-beta-20261020/`及上述/tmp证据，不入库构建物。

## 3. 决策记录

遵守已审核设计，不重开宏观架构：完整schema4索引/快照/事务，原虚拟路径挂载封存输入，Git对象通过私有无项目配置stub读取；关系计数独立于位置，只有唯一上下文才确认site配对。没有新解析器、名称猜关系或AI基础地图。

首个正式独立实施审核对旧84文件清单`ae00fe8fa4c17ee3d7de9be61d4ad3fb8b610d71f394074eabae28cb025a47eb`裁决 **NEEDS CORRECTION**。原始[报告](review/round-1/report.md)、[result](review/round-1/result.json)、[清单](review/round-1/candidate-manifest.json)原样保留。

| 原问题 | 本轮定向修正 |
|---|---|
| P1：ODR不变的constexpr/enum头变化无函数上下文事件，缺确切输入 | 用既有unit_files/files正读集和profile补充；输出路径/前后SHA、最多8项/8192字节预览、完整数量/集合哈希与明确序列化格式。ODR显式非权威。排除定义及主TU源码，以保留纯移行和其他函数体编辑独立性；适用边界在README/API/响应中明确。 |
| P2：非法UTF8被替代为其他字节 | 窗口严格解码，`source_not_utf8`为CLI exit2单JSON或HTTP422；非法窗口不返回替代文本，历史BLOB不改。内容/hash不符为`source_integrity_error`（503/exit2）。 |
| P3：source/source-diff缺哈希 | 返回整文件sha256/buffer_sha256、窗口range_sha256、begin/end原始字节偏移和encoding；页面可看两侧完整证据。 |

UI额外关闭忙碌时旧结果比较快捷入口，新浏览器断言必须等待匹配request_id/published及明确左右索引。修正只涉及10个既有候选文件，未改C++/schema/封存或发布实现；重新固定完整84文件，而非仅审补丁。

## 4. 结论与边界

**最终：M2-A实施与Codex完整自验通过，第2轮真实独立实施审核ACCEPT，必需01–20+22全PASS、21非本轮，无未关闭阻塞；源码已提交推送并创建[PR #3](https://github.com/Silver-Zhang/CodeWeave/pull/3)。** 旧设计ACCEPT未替代实施验收。独立会话=`06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6`，实际deepseek-flash[1m]（服务返回deepseek-flash）/max/auto。

上下文证据是observer TU级保守读集，不能证明运行时行为等价；同定义文件外部常量变化可能只有文件/源码Diff。独立审核须按真实合同判断这一边界是否可接受，不能强迫给好评。无TU增量复用/watcher/未保存缓冲/任意历史构建；普通依赖symlink、PCH/modules、完整隐式生命周期与全程序虚分派、真实私有项目性能非本轮保证。schema3只读，迁移必须新路径。

原始[最终独立报告](review/round-2/report.md)、[result](review/round-2/result.json)、[完整84文件清单](review/round-2/candidate-manifest.json)、[原生进程记录](review/round-2/native-execution.json)与[暂存树核验](review/round-2/tree-verification.json)原样/准确归档。原生续办14:48:18 UTC退出0、is_error=false，原始文本裁决与report/result哈希一致。报告SHA256=`194774587156e668a0bd75036445935c33490dbe2c3731734c5183c1c8a2abbf`；原始报告中的临时路径保持作者原文。

结果源码SHA=`7e1e0750de0c4259c961649804ba1907640fbbe2`，提交树=`e3a7cec6f5e4280c67d2065974a0e66d5360ab71`，与被接受候选每文件字节/模式完全一致；远端分支SHA已读回核验。main仍95620d8，PR open/unmerged；[交付记录](delivery.json)。工作流在本project/codeweave提交归档，远端最终身份另由实际Git核验，不自造本提交的自引用SHA。

非阻塞精度边界：N1是观察该实体的TU并集可能过报；N2是同文件外部常量可能只有文件/源码Diff。不得宣传为每函数精确依赖或行为等价。另记录未观察到的未来POST终态竞态、裸CR未单测和文档空格笔误，不在接受后擅改候选。

本地演示已实际运行于http://127.0.0.1:8000，真实多TU地图/两条调用边/快照源SHA通过。使用稳定源码README的启动命令；修改状态目录demo-project/main.cpp的literal和choose并保存，在网页刷新/比较查看Monaco双侧源码。用户验收尚待亲自试用。main合并/冻结、tag/release/M2-B均未执行，不自动进行。

## 5. 过程记录

| 日期 | 事件及保留的失败 |
|---|---|
| 2026-10-20 | 核对两仓库身份/干净状态，main含M0/M1；建指定分支/B任务，连续实现并跑通真实使用链路。 |
| 2026-10-20 | 额外探针发现闭包/局部类位置型USR导致移行伪变化，修正Clang ABI身份及ctor/dtor variant，新构建回归通过。早期导入拼写、越EOF和测试oracle错误保留并纠正；不修改参考结果迎合产品错误。 |
| 2026-10-20 | 首次workspace内安全fixture被VS Code Insiders自动git fetch/status触发自有fsmonitor，整体验收如实失败；父链与strace确认外部IDE来源，/tmp安全及完整回归通过。审核者也遇到同类隔离问题；原始日志保留，不能抹去失败或误归产品。 |
| 2026-10-20 | 原Opus调度出现工具/服务停滞，监督SIGINT；用户暂停后再恢复改Flash。第一次新目的地派发被自动审批拒绝，取得明确api.deepseek.com授权后才发送；配置未擅改。 |
| 2026-10-20 | Flash首段触及3600秒监管上限退出124，无裁决；原会话有新增独立证据后续办。首次正式原生is_error=false的裁决为NEEDS CORRECTION，旧报告原样归档；中断/超时不冒充多份正式审核。 |
| 2026-10-20 | 修正首测两项因TestClient默认testserver被已有Host保护拒绝；只改测试loopback地址重跑通过。新UI用例过早比较旧结果失败，补忙碌保护/精确等待后通过。完整当前门禁136/1/38/9通过、零Skip；全部失败日志仍本地保留。 |
| 2026-10-20 | 固定新4032清单，原会话开启正式第2轮独立审核；审核者全新构建完整门禁通过，正在自拟用例。修正版演示重启并保留历史，实测API哈希和Chromium通过；一次演示检查脚本误用字段名失败，纠正为文档begin/end后通过，未改产品。 |

| 2026-10-20 | 第2轮主段于14:40:02 UTC达到1800秒监管上限，退出124、无原生裁决/报告，真实完整门禁和专项证据保留。原件/副本84文件再核对一致；沿用同一会话/Flash/max/auto续办报告收口，不另计新候选或ACCEPT。 |

| 2026-10-20 | 同会话报告收口正常退出0/is_error=false，真实ACCEPT；独立旧P1/P2/P3均CLOSED，N1/N2明确非阻塞边界。原始report/result/清单及超时/原生最终记录归档；Codex复核双JUnit136/0/0/0和首末84文件一致。 |
| 2026-10-20 | 明确路径暂存；Git index逐文件SHA/模式核对，tree=e3a7cec6…；提交7e1e0750…且工作区干净，正常推送feature并核验远端SHA，建PR#3到main，未合并。工作流仅导航/本任务归档，无框架或旧任务改动。 |
