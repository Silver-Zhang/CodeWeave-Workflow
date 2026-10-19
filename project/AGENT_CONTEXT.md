# CodeWeave 接手上下文

1. 先读STATUS，再按需读当前任务。当前入口：[M0-R3独立审核](tasks/2026-10/20261019_04_m0-final-independent-review/README.md)，B模式，审核任务已完成；Claude独立裁决ACCEPT，等待用户冻结决定。
2. CodeWeave `feat/m0-code-index` HEAD `0e9c093a5a2456814c5543ec1e52089035b4bc2e`（M0-R3 候选，34文件清单摘要 `31f8d5a882ad98711c60264569a0720ce4d84ac870a6e2d6314edb53a6fadc7d`）；DevFlower `project/codeweave` 的本轮记录随后提交；接手仍须现场复核。
3. P1响应token前置拒绝、P2 status摘要/分页/字节预算均独立CLOSED；schema3/protocol2、事实和C++源码未改变。超长字段可用byte offset/base64分块无损恢复。
4. 独立新构建验收87 passed/零失败零Skip，正确Clang资源目录下backend88 passed（1既有Starlette warning）；自有30拒绝场景、真实300TU/301输入、极端字段和正常两TU全CLI通过。报告明确非严格盲审，记录提前读实施README和资源误配/审核脚本错误，错误轮不计PASS。
5. 用户已明确授权固定候选/必要材料发送Claude及限定审核操作。会话名CodeWeave独立审核，Opus5.5/xhigh、auto；原6c504510因配置恢复已停止，当前06fd5ee6保留历史并完成审核。源码只读；独立报告在审查专用detached worktree生成，再原文归档。
6. 环境Python3.12.3/CMake3.28.3/GNU C++13.3/LLVM18.1.3/Bubblewrap0.9.0/SQLite3.45.1；LLVM解包于.toolchain/llvm-18，resource-dir为其lib/clang/18。大日志在m0-final-independent-review-20261019-claude，监护记录在m0-final-hardening-20261019/claude-review，不入库。
7. 用户验收/冻结未发生；候选已提交/推送，未合并/tag/发布/M1。旧实施和审查档案保持原样；不访问RMC、核数据库、reference、F11或其他真实私有工程。若候选改变须重新绑定并复核，不能沿用本次ACCEPT。
