# M1 Round-2 独立审核检查表

此轮仅针对候选清单 `81b71e32a6094949338fba307a9b85983c463e0830cd4f1323d24b93c68711ae`。先按清单核对全部文件和 raw manifest SHA-256，结束时重复核对；不以 round-1 结果、实施说明或测试数量取代本轮证据。

1. **旧 P2 关闭条件**：以真实 Clang facts 的原始 UTF-8 byte column 作为事实/标题，转换为 Monaco 所需的 1-based UTF-16 code-unit column；覆盖 ASCII、Han、non-BMP emoji、混合前缀、LF/CRLF、definition 和 call edge、无效/边界列，并保持快照/index_id 身份。
2. **M1 事实内核**：HTTP/CLI 同库、同 index_id 的 status/search/show/calls/neighbors/source 相等；SQLite query 只读；分页/预算/错误稳定。
3. **本地安全**：启动时受信 DB/frontend、127.0.0.1、host/origin、任意路径及未知 source 拒绝；不执行分析命令。
4. **真实语义**：新 analyzer + Bubblewrap 构建自有 C++ 多 TU 索引；重载/static、调用实例、virtual/unknown、递归图与快照切换不伪造。
5. **前端**：Node22 全新依赖、typecheck/build/Vitest；真实 Chromium 搜索、局部图、展开/收起、预算、边/节点定位、unknown/virtual、错误/空/超时及 index 切换防串用。
6. **自主新增反例**：在预先定义的 CRLF + mixed Unicode call prefix fixture 中，预期 raw Clang column 按 UTF-8 bytes，Monaco position 按 UTF-16 code units，且 source line-number mapping 保持正确；该预期不从 analyzer 输出导出。

判定：关键验证缺失为 BLOCKED；P0/P1 或必需 P2 为 NEEDS_CORRECTION；仅全部合同通过且候选身份不变才 ACCEPT。
