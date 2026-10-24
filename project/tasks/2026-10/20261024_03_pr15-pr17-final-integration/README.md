# PR #15/#17 最终审核与条件式集成

任务与状态见 `task.json`；原始结构化审核意见见 `reviews/`，机器计数和身份见 `validation.json` / `source-manifests.json`。

## 1. 目标与范围

本任务按用户本轮授权核验 PR15→PR17 依赖，恢复真实 Claude 独立审核，验证工作台交互并做条件式普通合并。未授权强推、清理用户文件、改写旧审核、覆盖 Stable 或无限增加审核轮次。启动时 main e35dec1、PR15 cdc53cd、PR17 1e019b3，两 PR Draft；既有源码和 records 工作树干净。原有 Development/Stable/会话保持，新增 final-pr15/final-workbench 独立副本；未触碰 CodeWeave/RMC。

## 2. 做法与证据

最终 PR15：HEAD 546cba4ec92390eeef2218e119647485ee358ce1，tree c0b01275df195a2e74668442b82a93264c14ba3c，154 文件 CF 302125c7e87ff5f7bb4e6bcc57ac38ae0ecb375ac445d22410a5adc7ab9f28c9。
最终 PR17：HEAD a3b22f37e7e23f11fbc23d9e613e1662d91a17ec，tree 6c873146e04a3c820213e179a24931e9ba5e21df，173 文件 CF 0d1869aa19b15629fc0de6e68668fc8815a10505a77d214fd8a5662835f265a5；完整继承 PR15。按完整物理文件清单核验，拒绝符号/特殊文件和凭据/运行数据。

修复未知/损坏原生结果协议及多层 JSON 编码；普通工具参数语义保留。Metadata.put 仅对确认 SQLITE_BUSY 最多两次重试，连接/事务先关闭，不重发 Agent/permit；重复值单条原子语句不重复落盘。Claude 单次调用隐式重试设 0，本地真实 CLI 对合成502恰好1请求；认证、模型、effort 未更换。保留旧测试和断言，连线动画测试等待 React Flow 实际挂载。

完整命令：`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v`、`python3 tools/devflower.py check --baseline`、`python3 tests/host_isolation.py`、现有七组普通 Chromium/HTTP 脚本、六项语法、Node projection/editor tests、Node22 `tools/studio/workbench_ui/build.mjs`。最终 PR15 478 Python/6host/142browser/18JS，PR17 517/6/161/20；全部 exit0、FAIL/ERROR/SKIP0，构建字节一致。前置隔离审核环境有3个嵌套bwrap失败，宿主同候选执行通过，二者分列，不改断言或Skip。

同最终候选 Studio 真 Codex gpt-6.1-sol/xhigh 与 Claude Code claude-opus-5-5[1m]/high：PR15 2+3 回合；PR17 顺序2、汇合3、代码/研究路由各2、提前退出2、五轮10，共21，另有两真实新会话。初始化一次、当前轮输入/交接/请求SHA/原生UUID/真实进程回执绑定；五轮达到上限 FAILED 和显式停止 CANCELLED 是预期负例。暂停/刷新/恢复不重放；关闭视图不杀进程，第二写入者拒绝，显式关闭仅本任务终端退出。Codex 首次原生接管因占用未确认被拒，确认原进程已退后另行授权复测成功，原失败保留。Claude 新 HOME 完成自身主题/安全/指定工作区确认后恢复同一 SID，不拷贝全局认证或会话。

真实模型目录 Codex app-server 7 项、代理31项；请求/CLI申报与物理后端分列，后者和有效effort为 unknown。十项合成分类规则10/10、小分类器7/10、真实LLM10/10，平均约6.6秒；不代表泛化优势，成本unknown。Jev无独立凭据/权重，不调用、不接生产。

## 3. 决策记录

依据用户“PR15/#17最终审核、交互验收与条件式集成”授权建立新 run 7120c8604d44468eb353931ac0cbb384、独立合同。最多5轮源码审核、2次安全探测、2次基础设施恢复；健康探测2次各一个可控请求，第二次按同 HOME/明确UUID恢复。原 Issue14/16 的预算、NEEDS_CORRECTION、HTTP402/502 和 BLOCKED 不改写。本任务已用一次有意义的审核基础设施恢复；不使用 --last，不要求改判。用户最新明确批准 Opus5-5[1m]/high；实际物理参数 unknown。

固定旧 Stable 5816ba4776b3 的 Gate SHA 12f0b6aaf8d257e1ce0b87346e2f328089ab28fc96c52691719b7f28787630ab 由外部监督调用，待审 Controller 不批准自身。两候选同源完整验证、硬ACCEPT/必需finding关闭及Gate通过，且后续集成审核满足，才可 PR15→PR17 普通Merge Commit；禁止用PR15裁决替PR17、禁止晋升Stable。

## 4. 结论与边界

最终：R4 PR15 原始硬 ACCEPT、固定旧 Gate ACCEPT；R5 PR17 原始 NEEDS_CORRECTION，I16-A FAIL，其余22合同PASS。唯一未关闭必需缺陷 P1 `I16-A-MODEL-ADMISSION`：新鲜成功的原生目录省略默认模型，目录仍把默认值追加为可执行项，node_binding仍允许创建；尚无等效原生验证。不是断言当前账号的真实默认模型不可用。独立反例由受控runner原样复现，script exit0代表反例执行成功、行为测试1项FAIL；固定旧Gate真实BLOCKED/exit2。两PR保持Draft，main未合并。5轮源码审核及2次基础设施恢复均耗尽，按停止条件停止，不隐式第六轮，不把未经复审的新修改推为已验收。原生会话/日志/截图/视频仅本机archives，Git不存会话全文或隐藏推理。用户本人体验验收未进行。后续最小修复应统一模型目录/节点/新会话的准入，缺失默认项只能标待核验或另取等效原生验证，不能把“明确配置”当作“已验证可用”；需要新的明确任务和审核预算。当前 Development 试验服务未配置自动业务交付步骤，不能冒充产品自治交付已验证。

推荐入口：`python3 /home/workspace/DevFlower/.local/open-pr15-pr17-workbench.py`。已验证实际HTTP候选0d1869…，开发源码在development/final-workbench，页面标Development。原有 open-issue16-workbench.py 和 Stable 原样保留。服务/会话存储固定在本任务archive，不会清理临时目录丢失；CLI恢复按validation.json中的实际HOME/config root/cwd/UUID，禁止跨项目UUID猜测。

## 5. 过程记录

| 事件 | 真实结果与处理 |
|---|---|
| 原任务历史 | Issue16 R1纠正、R2 402、R3 502无有效裁决保留；新任务另建，不续旧轮数。 |
| 新R1 | 首次请求502无裁决；有界恢复新明确UUID后 NEEDS_CORRECTION，独立发现未知工具协议泄露。 |
| 新R2 | 修复后 ACCEPT_WITH_LIMITATIONS，未当作硬ACCEPT；审核隔离全套测试失败的尾诊断缺失。 |
| 新R3 | 补取完整嵌套沙箱失败诊断并与宿主通过结果分列；NEEDS_CORRECTION，发现非字符串type和多层编码仍可泄露。 |
| 额外真实负例 | CF893元数据OperationalError，确切原码unknown；同位置真实BUSY反例驱动有界元数据恢复。CF071循环首轮Claude600秒超时原样保留，后以独立授权的轻量真实调用验证调度，不伪称旧超时达五轮。 |
| 回归失败 | 一次连线DOM准备竞态；保留断言补就绪等待。同步时误带PR15旧会话实现导致CF749模型并发测试失败，恢复PR17实现仅保留一行结果协议入口，CF0d全套重验通过。 |
| 新R4 | 修复后硬ACCEPT。监督脚本变量覆盖使后处理exit1，实际审核进程exit0；原意见及坏元数据保留，追加原生UUID/cwd/原进程/源码合同恢复清单，未增加模型调用，固定Gate重验ACCEPT。 |
| 新R5 | 首次900秒超时、CLI退出-15，无有效裁决；20个请求含正常工具回合，14次缓冲返回，HTTP错误0，隐式重试0。最后一次同HOME/UUID恢复后取得原始NEEDS_CORRECTION，新P1模型准入反例成立；固定Gate拒绝，预算耗尽停止。 |

本机main已在干净工作树执行fetch/pull --ff-only，仍与远端e35dec1/tree a0c16fa一致。源码和两PR最新CI绿色不构成独立验收。原有开发worktree、Stable5816、认证、原生会话及证据未删除/覆盖。原始审核JSON按字节保留，反例脚本见reproduce_model_admission.py；Gate/身份/命令/日志哈希见validation.json。
