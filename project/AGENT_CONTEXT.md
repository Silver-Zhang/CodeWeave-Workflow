# CodeWeave 接手上下文

1. 先读 STATUS.md，再按需读 PROJECT.md 和当前任务 §1/§3/§4；不通读历史。
2. 当前入口：[M0-R2](tasks/2026-10/20261019_01_m0-correction-r2/README.md)及其[独立审核](tasks/2026-10/20261019_02_m0-r2-independent-review/README.md)，B 模式；审核为 ACCEPT，等待用户决定冻结/提交，不自动执行。
3. CodeWeave `feat/m0-code-index`，HEAD `608d4e7821868289028abcbdb89bfd87d9bb224c`（M0-R2 候选，33 文件清单 SHA-256 `290550ef33cfd58b3cbce4b93347388edef793218c4546cd91b40268fb8022c1`）；DevFlower `project/codeweave` 的任务与导航记录随本次归档提交。开始后仍需重新核验实际状态。
4. 架构保持 LibTooling → Python → SQLite → JSON CLI。protocol 2/schema 3；旧库只读拒绝、新路径重建；显式 project/dependency/toolchain/resource 根；单 TU 互斥配置拒绝。直接 analyzer 为内部受信组件，公开 CLI 始终 Bubblewrap。
5. 当前本机 LLVM/Clang 18.1.3 位于工作区 `.toolchain/llvm-18` 解包目录，Python 3.12.3、CMake 3.28.3、GNU C++ 13.3、Bubblewrap 0.9.0。专用入口全新构建：55 passed/0 failed/0 skipped；完整 backend 56 passed，均为实施者证据。
6. M0-R2 独立复核已完成并裁决 ACCEPT，候选已提交/推送；用户验收和冻结仍未发生。原 m0-independent-review、m0-correction、m0-correction-review 档案保持原样。
7. 不自动提交/推送/合并/发布或启动 M1；不访问 RMC、核数据库、reference、F11 或其他真实私有项目。本地大日志目录 m0-correction-r2-20261019；工作流只存摘要与候选清单。
