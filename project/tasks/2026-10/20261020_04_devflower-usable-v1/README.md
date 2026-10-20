# DevFlower Usable v1 — Issue #6

## 1. 目标与范围
完成网页画布版：工作区、Agent原生会话、工作流配置、任务授权、固定Stable真实开发、验证、独立Claude审核、自动修复复审及一个开发PR。不合并main，不改CodeWeave/RMC。CLI产品、桌面/VSCode包装后续；本轮停止于技术验收。

## 2. 做法与证据
main基线28cced14f5733dae293c237dbeb7bf9a842af71b。最终分支flow/devflower-usable-v1；本地/远端HEAD **c9fc36d8c7a3892e97a7e439eb682a0ca9b52990**；tree **b6733f39b9d13dcabc6a1c089242d55800120825**；完整83文件候选 **5816ba4776b35d625e163af805d656315a7c638ba4e60e576763b121d86b3821**。源码干净，正常push并独立读回。PR #7：https://github.com/Silver-Zhang/DevFlower/pull/7 ，OPEN、非Draft、CLEAN，mergedAt=null。

最终固定外部宿主回归255 Python + 6 host-isolation + 66真实HTTP/Chromium（9竞态/17身份/7工作区/33可用性），全exit0、0失败/错误/Skip；baseline及4项JS语法exit0，前后manifest不变。覆盖真实拖放、缩放、端口连线、插入、右键、撤销重做、保存竞态、A-B-A运行身份、授权预览、历史PR回执安全检查。

真实产品run **9c2ee39b5bb0489abede911e8f9319f4**：Studio授权后旧固定Stable1d2a4fa9执行真实Codex产品修复。外部监督一次性注入旧轮绑定故障，R1父进程13项中1失败、Claude83项中8失败，原始NEEDS_CORRECTION，自动反馈同一Codex修复。R2父进程13全过、Claude95全过，缺完整宿主证据而ACCEPT_WITH_LIMITATIONS，gate正确BLOCKED。补同候选255+6+65宿主证据后R3 Codex900.153秒超时exit-15、源码不变；核实退出后安全恢复一次。R4 Claude109项独立检查通过、原始ACCEPT。Git作者环境缺失曾阻断；仅补本仓库既有用户作者配置，外部监督重核原授权/候选/进程/旧gate后正常交付d17cb7d并创建PR7，最终COMPLETED。

交付后真实GUI发现旧Stable PR回执漏显示，Chromium先复现再修复兼容及commit/PR URL校验。首次扩展fixture引发旧单测3错误，修正历史图断言后完整255+6+66通过。新完整候选5816经外部review5代码ACCEPT后，才提交四路径兼容修复c9fc36d并更新同一PR、读回一致；不沿用先前候选ACCEPT。

最终真实图验证run **4180b07d383c433ebef1b930d34f0acf**：独立已审Stable5816，实际画布添加/配置/拖动并保存六节点，最多1轮、不改源码、不Git交付。父进程13项全过、两个原节点分别显示7和6，真实Codex/Claude会话/PID/候选/轮次/合同对应；刷新后同进程、同run、单次launch。Claude独立219项通过但原始ACCEPT_WITH_LIMITATIONS，保留可选P3 F-R1。此run仍**BLOCKED、run_accepted=false**，不改写为READY。

原始大证据根：`/home/workspace/DevFlower/archives/devflower-usable-v1-20261020`。产品运行：studio-functional-run/canvas-run2；最终回归：其full-regression/final-canvas-pr-compatibility-2；真实新图/截图/原生会话：studio-final-run；完整审核：independent-review-5；同候选最终补证：independent-review-5/closure；最终推送/PR读回：final-delivery.json、pr7-final-readback.json。失败日志、负面裁决及旧README备份均保留。

## 3. 决策记录
用户明确委托Codex操作GUI：授权主体用户、实际执行者Codex，不声称物理人类点击或独立人类易用性验收。Controller自身研发由固定外部监督与旧Stable自举，完整代码独立ACCEPT后才安装新固定副本；不使用待审Controller自批。

n8n仅作交互参考。画布承担节点配置、连接、任务入口与运行结果；设计草稿与固定运行快照隔离，历史运行明确标注旧图。两个真实run分别证明开发修复交付和新图映射，不混称后者已开发/交付。

外部审核1监督终止、2超时无裁决；3 NEEDS_CORRECTION；4 ACCEPT仅bootstrap-code-safety且整体false；5两阶段代码ACCEPT但G1/G2/G3待证据。第五轮同候选补证在原UUID执行118.998秒、exit0，实际读取PNG/原生回执/PR读回，原始**ACCEPT、issue6_complete=true**，关闭G1–G3。没有第6轮代码审核，前一报告未改写。

模型Codex请求gpt-6.1-sol/xhigh；Claude实际deepseek-flash[1m]、请求max，无法证明的resolved保持unknown。HOME/config/cwd/原生会话UUID及恢复位置仅保留在本地运行目录的native-session-locations.json，不上传会话记录。完整审核恢复先用本地档案根resume-deepseek-review.py --round 5 --describe，再按输出恢复，不用--last。

## 4. 结论与边界
**Issue6技术验收完成，PR7具备人工评审/合并技术条件，不自动合并main。** F1–F7/C1–C4/G1–G3关闭，无未关必需缺陷。可选P3 F-R1保留：异常Controller记录的boolean/float轮次可能与integer宽松相等；正常记录由父进程写整数、Agent无权写，最终独立审核认定非阻断加固项。用户对视觉/易用性的主观满意度不冒充已批准。

新图run的ACCEPT_WITH_LIMITATIONS/BLOCKED原样保留，整体外部ACCEPT不覆盖它。审核沙箱嵌套namespace/只读tmp错误、255项中3失败1错误、浏览器180秒超时均保留为环境限制；完整宿主回归另标实际执行者，不伪称Skip或Claude亲自全套通过。新图审核缺13探针脚本正文、核对回执并另造219例的限制保留。默认四断言仅smoke，后续任务须有具体测试合同；不宣称网络egress隔离。

正式已审Stable标准服务已启用，替换仅验证wrapper，保存工作流/会话/历史BLOCKED原样保留，没有启动新任务。打开：`python3 /home/workspace/DevFlower/archives/devflower-usable-v1-20261020/usable-v1-local-deployment/open-studio.py`。同目录service.json记录固定启动命令；服务停止后须据此恢复。私有URL仅本机日志，不发聊天。未来任务仍需独立授权，本次13断言不是所有未来任务的验收。

## 5. 过程记录
2026-10-20：环境/GitHub授权/中转诊断、旧小fixture和前四轮审核；否决候选自报计数协议，改父进程断言。旧fixture不作最终真实开发验收。

2026-10-21：画布交互修复；旧run9fe9ef…CANCELLED原样保留。新产品run完成真实故障、自动修复、补证、超时恢复与PR交付。实际GUI兼容缺陷修复后重新冻结回归、完整审查；真实新图与截图补齐，原第五轮补证ACCEPT。PR Ready后一次GraphQL读回EOF，仅重试读取确认成功；主线未变。归档一份五节README及机器摘要，原始大日志本地；本轮停止，不进入下一阶段。

本次研发记录整理仅同步本任务README、task/evidence摘要以及项目入口/索引到project/devflower；原始日志、截图、会话、运行状态与凭据不入库。evidence.json保留本地证据的相对索引与SHA256；这些索引不表示原始文件已上传。记录同步与源码PR交付分开，不合并main。
