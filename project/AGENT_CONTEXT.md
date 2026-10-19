# CodeWeave 接手上下文

1. 当前[B模式M1-Final](tasks/2026-10/20261019_06_m1-final-hardening/README.md)已完成研发/自验/真实独立ACCEPT，源码已交付。用户仅授权双方同候选通过后提交推送，用户正式验收/冻结、main合并/tag/release/M2分别另计。
2. CodeWeave feat/m1-interactive-map，base2d49db0e0b3d5e17cb95e9b876ffea0077e4ba8b，结果HEAD `6c3d1b8cf9c2ff3257c92840dd8531dcc1cceed7`，远端同SHA/源工作区干净。完整62文件SHA256 `f0714eb0def67f241fc14a442465202fcbf170e5e224e6bd32837a8d7795998c`，tree ffabf3d59a334349126ae2fec9923660d844e597逐字节/mode相等。工作流project/codeweave本轮baseb324efc8d42e6ebb0a7a43cf282ed853e7558b35，最终SHA/推送见交付回复及Git ref。
3. 只改App索引列表状态、前端稳定文档和2份新回归测试（4文件）：首次无选择自动最新，刷新合并已载历史/去重并保留选择，独立controller/request token忽略过期，列表错误分开且Retry；显式切换仍清空旧图/源码/请求。解析事实/schema3/protocol2、query和图预算未改。
4. 先写8组件断言，旧版7失败/1通过；修正后通过。正式完整新构建及ACCEPT后最终复验均110后端+fixture1、35前端、7真实Chromium，零Skip。首轮新增browser locator错误修正后全量重跑，失败trace保留。生产audit0，依赖锁未改，定向敏感信息/构建物扫描0、许可证metadata无缺项。
5. Codex额外真实22历史索引、浏览中发布新版本、历史原文字节/API比较、第二页/延迟/重叠/显式切换清空/503重试/真实空库6组PASS。Claude自有真实22+1索引变体也PASS；其第23次发布在页面加载前，不冒称独立验证了浏览中发布，该序列由Codex矩阵验证。角色和证据范围见任务。
6. neighbors确认N+1但未优化：31次暖缓存基线，10002实体/50200调用/16.82MB库，UI limit12为15持久连接114SQL约6.2ms；limit50为53/418约21.1ms。Claude独立复测7样本同计数、约6.14/21.08ms。只读URI/authorizer无写/DB hash不变；大响应query_limit，不能泛化到生产/冷缓存/大工程。复现脚本和摘要随任务，原始样本留本地。
7. Claude原UUID06fd5ee6-78e4-4dbd-ac8c-d442e9c97cb6，Opus5.5/xhigh/auto，一固定候选一轮正式审核，三次print启动（两次恢复）。首次监督暂停澄清环境/前提，exit0但raw is_error/无裁决；第二次随交互中断终止，退出码未捕获；第三次真正完成结构化ACCEPT，hash62/62一致。全部原始输出及失败harness留m1-final-hardening-20261019/round-1及attempt-1/2。
8. 原审查report/result/checklist在任务review原样归档，未改旧任务。harness两快照无分页、route cleanup、Python/work路径、主动切换应清空、原生option附着/可见的错误均非生产缺陷；纠正后真实运行才计PASS。auto曾拒绝递归清理，改新目录，不关闭保护，不把CLI exit0当ACCEPT。
9. Python工作空间.venv；LLVM .toolchain/llvm-18/usr/lib/llvm-18，resource lib/clang/18（非include）；Node22 .toolchain/node22/node_modules/node/bin，系统18不适用。真实Clang/Bubblewrap/Chromium在外层执行，产品隔离保持。大日志、索引、构建/trace均仅本地，不入Git。
10. Git只暂存明确本轮文件并核对完整tree，正常SSH agent/严格host校验/命令级URL改写，remote仍HTTPS，无force或凭据入库。不得自动开始M2或修改RMC/reference/F11/真实私有工程。下一步仅用户验收/冻结决定。
