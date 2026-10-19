# M1：HTTP API 与交互式 Code Map

## 1. 目标与范围

B模式。打通真实Clang索引→共用SQLite查询核心→本机只读FastAPI→React Flow局部调用图→Monaco保存快照。具备检索、调用/实体/来源查询、局部展开收起、真实调用点与源码导航。禁止M2、真实私有工程、main合并、tag或发布。

开工两个仓库staged/unstaged/untracked均空，现场核对remote：Silver-Zhang/CodeWeave.git、Silver-Zhang/DevFlower.git。CodeWeave从已审核M0 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`创建`feat/m1-interactive-map`；DevFlower `project/codeweave`起点`7faab07483567ce973c3b9be60e901c85144ad09`。远端起点一致、M1远端原不存在。M0用户正式冻结/main合并/发布未发生。

审核时HEAD为M0起点，完整60文件包含当时所有未提交新增，见[candidate-manifest.json](candidate-manifest.json)；清单SHA256 `fed1b6fe54a7844bd23e812182dafc54da79bd9ac19b404f37ce7d3659d6108e`。复制前后及审核结束，原工作区/独立副本逐文件hash与Git mode一致。最终结果commit **`2d49db0e0b3d5e17cb95e9b876ffea0077e4ba8b`**，Git tree `0fc291cb05addd7dd230315ab926519355be2447`；提交树60/60文件与接受候选的bytes/mode相等，工作区干净，已推送并核对远端同SHA。基线身份与结果提交分别记录。

## 2. 做法与证据

HTTP直接调用与CLI相同的query，增加稳定分页与局部neighbors；没有第二套解析器/事实库，不改C++/schema3/protocol2。数据库来自受信启动配置；只读SQLite、同源/本机Host、JSON错误、结果字节/数量上限，source只读登记快照。前端USR/call-instance去重、未知/虚分派明示，100节点/150调用点/24邻接请求；index切换和旧响应按身份隔离；Monaco原始模型只读保存快照，转换UTF8字节列为UTF16游标而不修改事实。

实际启动：`npm ci && npm run build`（frontend）；源码根`codeweave serve --database <index> --frontend frontend/dist`，访问127.0.0.1:8000。稳定契约见源码docs/http-api.md。自有fixtures允许演示，不嵌入静态伪图。

### Codex实际验证

环境Python3.12.3/SQLite3.45.1/CMake3.28.3/GNU13.3/LLVM18.1.3/Bubblewrap0.9.0；独立Node22.23.3/npm9.2.0，系统Node18不适用；Playwright1.64.1/Chromium156。Clang resource为lib/clang/18（含include/），真实命名空间测试在受控外层执行，产品Bubblewrap保持启用。

命令与大日志保留在本地`m1-interactive-map-20261019`，均为真实进程，退出码0的通过与失败尝试分开：

| 验证 | 结果/绑定 |
|---|---|
| `CODEWEAVE_LLVM_PREFIX=<llvm18> PYTHON=<venv> bash scripts/verify_m0.sh` | 全新构建87通过，0失败/Skip；logs/m0-fresh.log |
| 首候选完整`verify_m1.sh`及最终前端重验 | 后端103、fixture unittest1、前端6、真实Chromium2通过；logs/m1-complete-final.log及final-frontend-*；不替代后续修正版本 |
| Codex补查真实CLI/HTTP/Chromium Unicode | 原候选byte列54正确、UTF16预期50、实测游标54，退出1；unicode-check输入/oracle/facts/result/browser-process及original-rerun.log，原版证据已独立冻结 |
| 修正后实际源码完整`verify_m1.sh` | **110后端、1 fixture unittest、26前端、3真实Chromium均通过**，退出0、0 Skip；logs/correction-crlf-full.log。浏览器定位测试内含ASCII/汉字/emoji/组合/组合字符/定义前注释/行尾7场景，node及edge、API byte列、Monaco position和原始模型与快照相等，并覆盖CRLF/LF双TU |
| source/binary身份 | 本轮新构建main.cpp SHA256 `23ada77249c036cbacf2a21ddc6664601741f77d1d4cdb4d32cc85c817a2842b`；binary `8562b0369cf35e6affdefe011cc83a8e65cb6e7527fa0a0649de18ab15014e94`；不是旧binary/模拟器 |
| 最终ACCEPT后完整复验 | `bash scripts/verify_m1.sh`，2026-10-19 05:59:24–06:00:02 UTC，退出0：110后端、fixture unittest1、27前端、4真实Chromium；零Skip；logs/final-after-accept.log及.process.json，绑定最终fed1b6候选 |
| 边界/依赖检查 | 仓库结构检查、diff --check通过；生产audit由Monaco的2 low降至0，DOMPurify override3.4.17，锁文件固定；最终60文件敏感信息/构建物定向扫描0、生产许可证元数据无缺项，Git tree与接受候选逐文件一致；logs/final-production-audit.json、final-hygiene-license.json、source-commit.json |
| 提交版本的正常多文件演示 | 真实公共CLI为demo/source两TU/共享头新建索引，退出0，17实体/18调用实例/19观察，coverage=units_complete，诊断全0；demo/index-process.json、status.json。索引仅留本地，不入库 |

1条既有Starlette TestClient弃用warning、Monaco lazy chunk约695kB gzip是实际限制，未隐藏为0warning。CMake编译器探测的“skipped”不是pytest Skip；验收XML明确拒绝任何测试Skip。

### Claude独立审核与问题关闭

| 轮次 | 完整候选 | 原始裁决与处理 |
|---|---|---|
| 1 | 58文件，`8243cbbc1b891dab6a437cc19acdb62c59e8971ee578d285d59daf1a87006ff4` | **NEEDS_CORRECTION**，唯一必需P2 `M1-R1-P2-UNICODE-MONACO-COLUMN`；[原报告](review/round-1/report.md)、[机器结果](review/round-1/result.json)、[旧清单](review/round-1/manifest.json)。无确认P0/P1。独立新构建/完整M1、额外公共CLI/HTTP通过；其额外browser harness未形成独立PASS，报告如实区分 |
| 2 | 60文件，`81b71e32a6094949338fba307a9b85983c463e0830cd4f1323d24b93c68711ae` | **ACCEPT**，Unicode P2独立CLOSED；[原报告](review/round-2/report.md)、[机器结果](review/round-2/result.json)。独立完整110/26/3及自有CRLF混合字符浏览器65→61通过。但Codex新增时序反例失败，未满足自验关口，没有提交，未改写此ACCEPT |
| 3 | 最终60文件，`fed1b6fe54a7844bd23e812182dafc54da79bd9ac19b404f37ce7d3659d6108e` | **ACCEPT**，[原报告](review/round-3/report.md)、[机器结果](review/round-3/result.json)。独立新构建完整110/27/4，额外call-edge保持及index切换时序变体PASS，开始/结束60文件一致，两项问题独立CLOSED |

P2根因：SourcePanel直接把Clang UTF8物理字节列传给Monaco UTF16坐标。修正为sourceLocation单一展示转换，按Unicode码点累计UTF8字节与UTF16单位、内部byte偏移向前夹取，处理非法数值/越界/行终止符；原API、标题和facts保留字节列。16项基础加4项CRLF/范围测试与真实7场景回归支持Codex自验关闭；**第二轮已独立关闭**。没有改旧审查结论或把Codex反例冒称Claude首次发现。

### 追加导航时序问题（Codex发现）

`M1-CODEX-P2-SELECTION-RACE`：真实Chromium先在ping图选pong并展开，只延迟原始neighbors请求，再点ping，释放原请求（route.continue未改写facts/response），选中项由ping变回pong。原版输入/脚本及result.json/run.log在navigation-race，退出1，绑定81b71e候选。问题源于App.expand完成时无条件select(expandedEntity)，覆盖了用户更晚的node/callsite选择。

修正为非reset扩展只合并事实，不重设选择；reset/root定位继续选中目标，既有epoch/index隔离保留。组件与真实API/Clang/Chromium时序回归均增加，最新完整脚本logs/navigation-full.log退出0：**110后端、27前端、4真实浏览器、fixture unittest1，零Skip**。Codex自验及第三轮独立复核均关闭。旧R2 ACCEPT原文保留，当时没有提交/推送；只有最终新候选第三轮ACCEPT及最终自验后才执行Git交付。

## 3. 决策记录

用户2026-10-19 M1请求授权实施、自测、真实Claude修复闭环；只有“Codex自验通过、Claude真实ACCEPT、同完整候选不变”才能自动commit/push两个指定分支。未授予main合并、删除分支、tag/release、M2或私有项目操作。最多5轮，两轮无实质进展或关键证据/服务阻塞则停止自动提交。

最新用户原文“还是沿用原来的Claude对话和模型以及强度”覆盖附件每轮新会话条款：使用CodeWeave独立审核UUID `06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6`，Opus5.5/xhigh/auto，不fork。CLI2.1.303/auth有效，实际init和API参数记录确认模型/effort。每轮重新核验完整候选，保留原始负面结论；并非严格新会话盲审。第一轮先独立合同/源码/实测，之后才接收Codex的Unicode原始反例。

变更卡：风险为身份串用、无界图、路径越界、展示坐标差；只改适配/交互与必要查询接口，不变解析事实；真实Clang/API/浏览器和独立反例验证。失败继续定向修复，不放宽断言或替代独立裁决；候选改变重审，不reset/clean。

## 4. 结论与边界

**M1实施、自验与三轮独立复核已完成；最终唯一独立裁决ACCEPT，无未关闭P0/P1或必需P2。** Unicode及异步选择回退均已独立CLOSED；最终完整自验与审核绑定同一fed1b6候选。CodeWeave结果commit `2d49db0e0b3d5e17cb95e9b876ffea0077e4ba8b`已正常推送到`origin/feat/m1-interactive-map`，远端精确SHA已核对；未修改main、M0分支或tag。DevFlower本任务及必要导航随`project/codeweave`归档，其最终提交SHA与两仓库远端验证见本轮交付回复及本地delivery.json，避免把工作流SHA写成源码SHA。

任务状态“已完成”仅指本轮研发、自验、独立复核与归档；**M1用户验收/正式冻结、main合并和发布均未发生**。任何后续源码变化须重新绑定清单，不能复用旧版本裁决。

已知允许边界：本机可信启动配置/无网络部署认证；高级布局、超大工程性能、完整隐式生命周期和全程序虚分派、其他源码编码、M2/版本差异不在本轮范围。图显示静态调用实例，不保证运行必执行；未知目标保留未知。源码当前磁盘变化由历史快照隔离，不声称自动增量检测。

下一步由用户对已交付M1进行实际验收，再决定冻结；不自动进入M2、合并main或发布。两仓库推送分别核对，不具备原子性，失败不得伪称同步。

## 5. 过程记录

| 日期 | 实际事件/失败与纠正 |
|---|---|
| 2026-10-19 | 干净基线/远端核对、B建档及M1分支；系统Node18不满足当前Vite，独立安装Node22；外部UI连接器无浏览器，实际安装官方Playwright/Chromium进行headless UI |
| 2026-10-19 | API初验1失败为测试误认为删除定义即删除共享头声明，改为声明存在/定义消失；浏览器手算local列20应21、接收者b列48应callee run列50，均按源码语义澄清，未变解析事实；失败日志api/e2e-initial/e2e-second保留，首trace被后续覆盖仅日志存留，后轮trace单独归档 |
| 2026-10-19 | Claude后台注册占用使首次-p退出1，stop该已完成后台占用后同UUID恢复，无新对话；缺参数工具循环被暂停并同会话以具体Read恢复；所有启动/恢复输出保留 |
| 2026-10-19 | Claude auto分类器超时；按用户备用授权Codex代执行其未改写harness，因传ccdb文件退出1，单独署名。随后Claude自行修正路径/目录/USR并实际API PASS；其browser import/strict locator/NBSP/异步等待失败如实标harness未完成，不是产品PASS/FAIL |
| 2026-10-19 | Codex新增Unicode实测失败后，先保持58文件候选不变；在独立临时副本验证补丁。曾误复用补查输出目录，原文归档unicode-prototype-evidence并声明旧identity字段无效，再真实重现原候选54失败，原版证据冻结。后续按候选分目录，未改生产/审核副本 |
| 2026-10-19 | 临时副本首次相对路径断言/受限sandbox验证不计通过，精确停止该测试树（143）；独立缓存及外层完整复验通过。第一轮原文NEEDS_CORRECTION归档后，才把补丁应用正式源，补齐CRLF/字节内部/范围边界并完整重验 |
| 2026-10-19 | 60文件预检e29eff…未送审，追加CRLF/clamp覆盖后重新全验并固定最终81b71e…；第二轮实际print进程仍同UUID/模型/强度，新增流事件仅用于监护，不输出内部推理 |

| 2026-10-19 | R2原文ACCEPT归档，但Codex追加长请求+最后节点选择反例失败，主动关闭提交关口；R2未改写为负面裁决。停止该轮源冻结后定向修正App一处异步重选，增组件/真实请求时序回归，完整110/27/4通过，再固定fed1b6…送第3轮同会话全审。 |

| 2026-10-19 | 第三轮真实ACCEPT，源码及副本仍fed1b6…；其后Codex再次全新构建完整110后端/27前端/4 Chromium/fixture1，退出0、0 Skip（logs/final-after-accept.log/process.json）。生产audit0，60文件敏感信息/构建物扫描0、许可证元数据无缺项，远端M1不存在/工作流仍7faab074，无并发改动。执行提交推送依据用户M1§8条件授权，不从审核者建议推导权限。 |
| 2026-10-19 | 按35个明确源码路径暂存并提交，提交前后Git tree与60文件接受候选完全相等。HTTPS首次push因无交互凭据退出128；使用已有SSH agent及严格host key校验、仅本次命令URL改写后，正常push退出0，origin仍保留HTTPS。未新增凭据或修改全局Git配置；source-push.json保留成功原始输出。 |
| 2026-10-19 | 使用最终已提交源码的自有多文件fixture生成独立demo索引，公共CLI退出0、17实体/18调用/2TU/3输入、诊断0。仅在本地审查目录保留数据库、命令与输出；完成当前任务归档，不修改历史任务。 |
