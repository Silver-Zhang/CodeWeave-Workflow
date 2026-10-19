# M1 Round-3 独立审核检查表

本轮仅绑定 candidate manifest `fed1b6fe54a7844bd23e812182dafc54da79bd9ac19b404f37ce7d3659d6108e`；开始/结束核验所有文件、bytes、SHA-256 和 mode。旧轮结论只作历史线索，不是本轮结论。

1. 完整 M1：全新 analyzer，真实 Clang/Bubblewrap、完整 `verify_m1.sh`，Node22 type/build/Vitest/Chromium；HTTP/CLI 同一 query/index_id/快照、只读/API 安全、图真实 facts、unknown/virtual、分页/预算/错误、身份/环/收起/索引切换。
2. R1 Unicode 关闭不得回归：Clang raw UTF-8 column 原样保留，Monaco 为 UTF-16 code-unit position；调用边/节点、LF/CRLF、Han/non-BMP/组合字符。
3. R3 navigation race：预定义预期为——等待中的旧 `neighbors` response 释放后不得覆盖期间较新的选择、source/evidence 或 index identity；只能合并属于当前 index 的图事实。至少一项真实 Chromium route-continue 时序反例。
4. 自主变体：展开旧实体时选择一个 call edge（而不只是节点），再选择另一个实体并切换 index；释放旧响应后，UI 不得回退选择、source、evidence 或图身份。
5. 完整源码/依赖/隐私/资源释放审查；P0/P1/必需P2 失败为 NEEDS_CORRECTION，关键实证缺失为 BLOCKED，唯有无阻塞才 ACCEPT。
