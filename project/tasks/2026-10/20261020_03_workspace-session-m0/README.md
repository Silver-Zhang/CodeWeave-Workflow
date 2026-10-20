# DF-WS-M0：Workspace Manager 与只读会话聚合

## 1. 目标与范围
任务卡为 [Issue #4](https://github.com/Silver-Zhang/DevFlower/issues/4)，依 AGENTS/WORKFLOW 执行 B 模式。基线 main `f7307f10d3fac01dfd6ed24f41cb4d2bec2d4912`，开发分支 `flow/workspace-session-m0`。唯一源码 checkout `/home/workspace/DevFlower/DevFlower`；本实例在 records/project，过程在 archives/workspace-session-m0-20261020。只读会话发现、受限元数据索引、业务工作区选择；不改 Controller、CodeWeave/RMC、原始会话或认证。

## 2. 做法与证据
实际命令：`python3 tools/devflower_studio.py --workspace <Studio索引目录> --project-root <业务工作区> --session-profiles <显式登记JSON>`。业务工作区与原有草稿存储分开；Codex/Claude 原生ID、提供方和存储Profile分别保留，恢复命令只复制不执行，能力始终未验证；Copilot unsupported。
旧基线132单元、host4、baseline/语法通过。当前第三轮完整自验：164单元（132原有+32新增）、host4、Chromium旧竞态9、身份竞态17、新工作区7全部通过，0失败/错误/Skip；baseline与两模块语法退出0。真实命令、时长和日志在 selftest-3/results.json。CI已接入M0单元和模块语法，浏览器为本地可复现证据。
真实只读复验发现Codex1/Claude2，检查的6个原生/认证文件哈希未变；旧目录中的超大/非会话文件如实列为覆盖缺口。只登记本任务明确UUID，不把CodeWeave同cwd的其他会话归入本项目；不复制/外发原始对话。
第三轮冻结61文件：候选 `059dcdee10ddf5175f32f01e512cd05f16a1109afc228099caf76bbfac98d8d6`，tree `4b61d1e62ab9dfbc4a1501d3d0b8da931666a74b`，合同 `79d286b0eb5b9e717efe5e992029646a769330f76d83a37810c782bcdae1b0cd`。各轮身份、实际PID/退出及原始裁决哈希见 review-evidence.json，完整报告仅本地 round-N/review/raw-verdict.json。

## 3. 决策记录
Issue明确授权指定开发分支commit/push/PR，须先全部测试、真实独立ACCEPT和候选核对；禁止main合并、force、删分支、原生历史修改及CodeWeave/RMC改动。固定外部监督不导入待审Controller，不让新框架批准自身。
按用户要求先清理worktree并同步云端：PR #2/#3已由外部合并；仅移除无源码修改/无进程占用的Studio-validation、Studio-stabilization、尚未写实现的Workspace-session-m0，以及纯Python缓存；未删分支。主checkout先与origin/main核对HEAD/tree一致，再切本任务分支；records既有修改及所有archives/原生会话保留。
Claude Code2.1.303；原生modelUsage为deepseek-flash[1m]；请求effort=max，resolved字段不可得，记unknown。专属UUID `85567117-650e-42a6-8734-e52212615bf6`，cwd=/home/workspace/DevFlower，持久HOME=/home/workspace/DevFlower/archives/workspace-session-m0-20261020/runtime/independent-reviewer。设置文件只读引用，未复制整个默认HOME或原生历史。
原生文件：上述HOME下 `.claude/projects/-home-workspace-DevFlower/85567117-650e-42a6-8734-e52212615bf6.jsonl`。默认 `/home/silver/.claude` 无此UUID，单纯切cwd不会切换历史库。R2实际--resume退出0并返回同一UUID，旧历史前缀哈希未变；仅证明本任务审核会话可续接，不泛化到其他会话/提供方。该会话原生cwd曾随测试命令变化，产品保守标cwd_changed并隐藏复制命令；监督记录仍有明确的原始运行环境。审核进程退出后可用：
```bash
cd /home/workspace/DevFlower
HOME=/home/workspace/DevFlower/archives/workspace-session-m0-20261020/runtime/independent-reviewer \
/home/silver/.local/share/claude/versions/2.1.303 \
  --settings /home/workspace/DevFlower/archives/studio-v01-stabilization-20261020/runtime/independent-reviewer/.claude/settings.json \
  --resume 85567117-650e-42a6-8734-e52212615bf6 \
  --model 'deepseek-flash[1m]' --effort max
```

## 4. 结论与边界
R1原始裁决 NEEDS_CORRECTION：F1特殊文件覆盖漏报，F2控制字符测试夹具无效，F3Unicode surrogate使整份快照422。R2原始裁决 NEEDS_CORRECTION：F1–F3 CLOSED，新增F4统计/读取间文件大小竞态、F5文件类型替换时可能打开特殊文件数据流。R3原始裁决 **ACCEPT**：F1–F5全部CLOSED，无未关必需缺陷；独立新增修复反例17项、关闭复验13项、范围反例25项、浏览器9项通过。R3 PID601117，exit0，无超时，用时1257.74秒；三轮真实审核用时分别870.10/768.57/1257.74秒，收到ACCEPT后停止，不跑满5轮。
最终外部核验61文件内容/Git可执行位、合同、164单元等8组自验、真实session/退出及原始裁决均一致；按11条明确路径暂存，git write-tree与被审tree相同。源码提交 `e339c5ef62866f35de89da54011d18c88d3fc2d7` 已发布并读回，本地正常fast-forward且干净。[PR #5](https://github.com/Silver-Zhang/DevFlower/pull/5) 已创建，base=main，未合并。项目记录独立归档于project/devflower；跨分支发布回执在本任务archives/delivery.json，未声称原子交付。
仅支持已观测的Codex/Claude主会话布局，预算/权限/损坏/部分写入/未扫描均明确降级；Linux O_PATH与/proc/self/fd用于固定普通inode，无支持则失败封闭。产品没有原生会话写入或浏览器执行接口。只读真实样本为Codex1/Claude2，不代表全面兼容原生私有格式；产品可恢复状态仍为未验证，只有本任务Claude审核会话有实际原生续接证据。Claude不能直接访问原始用户会话/认证，只审查聚合证据；宿主隔离由外部runner执行。CI覆盖单元与语法，浏览器证据来自本地真实Chromium；未声称存在ST-R02/ST-R03测试。安全设备验证使用/dev/null元数据且不打开数据流，未创建设备节点。
任务卡足以启动和推进实现/验证/复审；仍依赖本地CLI认证、配置根与固定外部监督。不能把“元数据可发现”当“原生可恢复”；本轮已另取任务自建会话的真实续接证据。Issue与AGENTS/WORKFLOW足以驱动本次实现、自验、三轮真实复审和PR交付，无需用户逐轮中转报告；任务卡不能代替实际CLI认证、Profile根目录、浏览器和既有固定外部监督配置。临时状态页与worktree清理由用户另外明确提出，未混入M0源码。下一步仅由用户决定PR合并；未自动进入M1。

## 5. 过程记录
2026-10-20：输出14行预检、核验远端/main/全部工作树与脏文件，建任务并跑基线；按用户要求清理到源码+records两个worktree。
初版NUL夹具构造错误及浏览器route重复处理失败均保留。R1进一步发现测试仍用了字面\n，之前“已修正”的说明过宽；R2改真实换行并断言invalid_path且没有partial_write。R2修复前29项中2失败4错误，修复后29/29。R3修复前32项4失败，修复后32/32，完整164/164。
R1审核沙箱内嵌套bwrap无权限（2失败2错误）为环境失败。Claude独立设计的外部脚本由Codex固定runner实际执行4/4成功，PID565909、exit0、脚本/输出哈希齐全；R1未看到该回执，原意见保持不改，R2独立核验后接受宿主证据。
补充真实样本探测曾错误期待cwd_changed会话有复制命令，TypeError日志保留；按实际原生元数据改为要求保守降级，产品与判据未改。原用户会话无网络续接；只有本任务新建审核会话被真实--resume。
用户要求状态页：临时只读观察页 http://127.0.0.1:8766/，每3秒读取外部回执与PID/start；不是Controller权威状态，不展示全文或隐藏推理。实现/进程回执在本任务archives/observer，未进入候选源码。
Git HTTPS dry-run退出128（缺本地登录凭据），未改变远端；已连接GitHub通道可读，交付时只允许已授权正常提交/ref更新并读回，不降低审核门禁。

第三轮ACCEPT后收尾：本地Git HTTPS无凭据，使用已授权GitHub连接创建精确tree/单父提交/任务分支，读回后本地正常fast-forward；无force/reset、无main修改。最终门禁首个脚本把本地umask的0664误比为冻结器规范Git模式0644，记录该检查器错误并按同一冻结规则核验可执行位，源码/候选/合同均未改变；通过后才交付。所有原始审核及失败日志仍在本地。

云端读回：相同源码SHA的Studio contracts push与pull_request工作流均completed/success（run39386769828、39386863737）；PR #5 mergeable=true、mergeable_state=clean，未合并。
