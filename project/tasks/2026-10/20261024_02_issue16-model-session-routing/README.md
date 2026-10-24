# Issue16：模型、会话、真实交接与 Sim 交互

## 1. 目标与范围

任务 `20261024_02_issue16-model-session-routing`，B 模式，run `396d0ad7c4644a26bb6c70812dc3ef39`。Issue16 原合同 raw SHA `dffdbc0bd1fb254e89ade0e8bcfefe0031a94f49673b0ed2df3233ea6f560467` 保留；用户追加 Sim 整体交互、布局、动效及浅色/深色/系统主题，最终合同 SHA `e7ad96a1e3a125e61b5585ffa0a2c43c235f7e73be34fc98248321a030fc9da6`。同任务最多5轮审核，没有重置旧预算。继承 PR15，不合并 main，不晋升/覆盖 Stable，不修改 CodeWeave/RMC，不删除会话/历史。

## 2. 做法与证据

[Draft PR17](https://github.com/Silver-Zhang/DevFlower/pull/17) 以 `flow/workbench-ux-polish` 为 base，保留 PR15/cdc53cd 全部实现。当前 HEAD `1e019b35a92c7ddeb4f3ef9f02cbfa54c88ba3ff`，tree `496bf759487112ebd34b58f362956996d8da3aca`，173文件完整候选 SHA256 `893aaa35415a1017e0b0be1e270ce67021722939b6c4a8115cc46aed2f8e51be`。清单见 source-manifest.json，原始审核/进程记录见 review-r3-process.json，机器证据摘要见 evidence.json。

- 同候选506 Python、6宿主隔离、161 Chromium/HTTP、12投影+8编辑器测试全部 exit0，FAIL/ERROR/SKIP=0；Baseline、6语法、逐字节重建通过，源码未改变。原有测试保留。
- 模型根因是预登记 Profile/静态数据被当作主要目录及失败/缓存来源不透明。改为按 Profile 实际发现、刷新、TTL/失败、权限与 effort 分离。当前 Codex0.163.0 实测 model/list7，Claude2.1.303 中转站 /v1/models 实测31；此前404仅历史，目录不是执行授权。异常数组/null/标量响应已复现为 AttributeError，最小修复后保留旧目录并标 stale，新增负例。
- 关闭/Escape/焦点/每标签未保存三选；视图关闭不停止 Agent。真实字段合同、activation/round/hash 与 A–F 下游请求检查器；初始化幂等、迟到输入隔离；确定性规则优先 Router、只读可选分类、严格Schema/阈值/超时/default/权限校验。
- Sim 官方v0.9.32实际编辑器与源码已检查，6组同候选并排图仅本地。224px侧栏/320px检查器、可调宽与收起、上下文搜索创建、端口空白连建、右键多选复制、连线插入与一次撤销、曲线箭头、键盘/窄屏、减少动态效果。直接复用两个 Apache2 Sim 交互 primitives，保留 LICENSE/NOTICE/来源和修改标记；未复制品牌资源。
- 真实模型分列：当前冻结源码上顺序、两路只读并发汇合（下游一次）、代码与研究分类路由，共4运行/9原生调用，全部COMPLETED，4个真实worker exit0且stderr空。暂停/刷新/恢复同run；实际请求哈希、上游来源、初始化及原生SID均绑定。两工具新会话成功；5个工作流会话的HTTP/历史/HOME/UUID一致。原生Codex终端实际加载旧回答标记，关闭视图保持进程、第二写入者HTTP400、显式关闭仅停止拥有进程。
- Jev核实为TypeSafe Jev/System One，有官方类型决策API和MIT SDK；SDK许可不等于权重许可。无独立授权key/本地权重权利证据，调用0，不伪造集成。固定合成集n10：规则10/10、独立训练轻量分类器7/10、真实Opus分类10/10，LLM mean8017ms/P507775ms/P9510266ms、fallback0、成本unknown；小样本不代表泛化。

## 3. 决策记录

允许正常源码/记录 commit、push 和 Draft PR；禁止 main合并、Stable晋升、force/reset/clean、删除原生会话及历史。源码与框架记录分仓，逐路径暂存，隐私检查后正常推送与远端读回；原始日志/截图/视频/认证/HOME不入库。用户最新明确批准 Claude `claude-opus-5-5[1m] / high`，Codex `gpt-6.1-sol / xhigh`。CLI回报与物理后端/实际effort分开，无法独立证明的参数unknown。

固定外部监督器导入旧 Stable5816 Gate；待审 Controller 无自批权限。R1–R5上限不重置，R1 NEEDS_CORRECTION、R2 HTTP402/no verdict 原件保留，本次为R3。基础设施安全重试最多2。

## 4. 结论与边界

独立审核本轮 **无有效裁决（连续中转站502）**，不能将外部BLOCKED处置冒充Claude原始裁决；最终关口 **BLOCKED**，外部处置退出码2。完整正向Gate未执行；固定旧Gate的旧裁决拒绝负例实际exit2。技术验收未通过，用户本人UX仍待确认，保持Draft，不合并/晋升。剩余阻断以原始裁决和Gate reason为准：R3 exact-session Claude review received repeated relay HTTP502; no valid current-candidate verdict. Owned native process stopped at retry-bound discovery, exit -15. No further retry this turn.

原始R1 NEEDS_CORRECTION、R2服务402，以及旧源码的worker失败/超时/原生开发核验BLOCKED均不改写。原生Codex曾发现非法输入/结束节点插入，真实浏览器复现，现增加双边连接校验与过滤；循环预览反例同样修复。首次回归观察器/录屏依赖错误单列，不计为产品成功。

本机 Development 入口 `python3 /home/workspace/DevFlower/.local/open-issue16-workbench.py`，已验证，页面http://127.0.0.1:45909；是Development，不是批准Stable。Stable5816文件保持原样，本次健康检查显示其旧服务未运行，未覆盖或偷偷重启。只读原生Agent无法访问worktree之外的共用Git元数据时，会报告git状态不可读；候选身份由固定外部manifest提供。

## 5. 过程记录

|阶段|真实结果|
|---|---|
|预检|main e35dec1/tree a0c16fa6；PR15 Draft；独立分支保留其源码；所有worktree/会话/认证保护。|
|初次实施与R1|模型/关闭/交接/Router；R1 NEEDS_CORRECTION，worker异常收尾、Sim实测、Jev来源、缓存和ARIA问题原件保留。|
|R2|服务HTTP402/exit1，没有有效裁决；停止重复计费错误重试。|
|用户追加与修复|用户授权Opus55[1m]/high；真实通道恢复；Sim整体交互+双主题，实际源码复用保留许可；开发核验提出边插入缺陷，最小修复与完整重验。|
|当前冻结与补证|173文件SHA/tree固定；506/6/161/20回归；真实顺序/汇合/两路由/新会话/原生恢复和停止；操作视频与官方Sim并排图本地保存。|
|R3与交付|无有效裁决（连续中转站502）；服务连续502，原生CLI内部默认重试10在发现已发生5次错误后停止，实际请求6次含在途；保留超额重试事实，外部监督器改为CLAUDE_CODE_MAX_RETRIES=0并通过本地真实CLI/合成502单请求测试；本轮不再复审。Gate BLOCKED/exit2；最新源码已推送PR17，研发摘要同步project/devflower。|

审核会话 HOME `/home/workspace/DevFlower/archives/devflower-issue16-20261024/runtime/r1`，配置根 `/home/workspace/DevFlower/archives/devflower-issue16-20261024/runtime/r1/.claude`，cwd `/home/workspace/DevFlower`，SID `19e82b7a-d457-4b61-b6a3-1dc0dea84d2b`；原生位置 `/home/workspace/DevFlower/archives/devflower-issue16-20261024/runtime/r1/.claude/projects/-home-workspace-DevFlower/19e82b7a-d457-4b61-b6a3-1dc0dea84d2b.jsonl`。恢复入口 `python3 /home/workspace/DevFlower/.local/resume-issue16-review.py` 使用明确UUID/原HOME与只读认证挂载，拒绝第二写入者，不能--last。用户UX、合并和Stable批准均不从审核/CI自动推导。
