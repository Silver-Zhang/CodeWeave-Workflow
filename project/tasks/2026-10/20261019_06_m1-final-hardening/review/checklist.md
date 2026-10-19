# M1-Final Round-1 独立审核检查表

绑定候选 raw manifest SHA `f0714eb0def67f241fc14a442465202fcbf170e5e224e6bd32837a8d7795998c`；开始/结束逐文件 bytes、SHA-256、mode 核验。

1. **Refresh 状态模型**：初次无选择自动最新；已选历史刷新保持 index_id、图、source/evidence；历史第二页/后页刷新仍在 options；新索引发布只增选项；明确切换清空旧 graph/source/request；空库、刷新失败保留有效视图并可重试。
2. **竞态**：refresh 分页/重叠列表请求/用户选择/StrictMode/AbortController；旧 response 不覆盖新选择或错误；旧 neighbors delayed selection race 不回归。
3. **真实全合同**：CLI/HTTP 同一 readonly query/index_id/facts；错误、分页、byte budget、path/host/origin 边界；真实 Clang/Bubblewrap、unknown/virtual、局部图预算、快照身份、UTF-8 byte→Monaco UTF-16。
4. **独立新增反例**：预先定义至少 22 个真实索引/分页时序变体（或等价真实 SQLite/Chromium 变体），在历史选中时重叠 refresh、发布新索引并释放旧页；预期历史仍可选且视图不丢，新索引出现；不得手写调用关系或伪造事实。
5. **性能**：先静态审查 neighbors 连接/query 逻辑，再独立核对性能原始数据与测量边界；至少代表规模复测连接次数/SQL/响应/字节预算/只读和随邻居规模变化。不因单次耗时宣称优化或故障。
6. **工程/依赖/隐私**：完整新构建、前端 build/test/Chromium，无关键 skip；候选和旧报告只读。

裁决：关键证据缺失 BLOCKED；P0/P1/本轮必需P2未关 NEEDS_CORRECTION；充分证据且无阻塞 ACCEPT。
