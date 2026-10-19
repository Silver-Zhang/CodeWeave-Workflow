# CodeWeave M1 独立审核检查表（round-1）

候选冻结后按本表执行；不以实施报告、自验结论或测试数量替代实证。

## A. 候选身份与范围

- [ ] 读取并按候选清单算法核对 manifest SHA `8243cbbc1b891dab6a437cc19acdb62c59e8971ee578d285d59daf1a87006ff4`。
- [ ] 逐文件核对 path、文件内容 SHA-256、mode，包含新增、删除、tracked、untracked 身份；结束时重核。
- [ ] 记录 `status.txt`、staged/unstaged patch、基线 `0e9c093a5a2456814c5543ec1e52089035b4bc2e`；不修改候选。

## B. HTTP/CLI 事实统一与安全

- [ ] HTTP 与 CLI 对相同数据库/index_id 的 status、search、show、callers、callees、source、邻接图逐项比对。
- [ ] 核对 HTTP 是否复用 M0 `query()`，保留 USR、instance_id、dispatch、anchors、未知关系和快照身份。
- [ ] 真实 index_id 切换、旧索引/失败索引、过期磁盘源码、损坏/不存在数据库。
- [ ] 本机只读绑定、127.0.0.1 默认监听、CORS、任意路径/路径穿越/文件读取、SQL 注入、JSON 错误状态、分页/limit/响应预算。
- [ ] HTTP 查询不写 DB、不执行编译命令、不访问未授权路径；并发/资源释放和超时行为。

## C. 真实索引语义

- [ ] 自有多 TU C++ fixture 真实 Clang/Bubblewrap 生成索引；重载、同名 static/作用域、声明/定义归并。
- [ ] 直接调用、调用点、宏调用点、virtual、unknown-function-pointer/dependent 的语义不伪造运行轨迹。
- [ ] HTTP/CLI 调用者/被调用者和邻接图与 SQLite/CLI 相符；递归环不会无限展开。
- [ ] source 使用索引快照，不读取修改后的磁盘源码；index_id 不串数据。

## D. 前端真实行为

- [ ] 全新 Node22 依赖安装/TypeScript 类型检查/构建；不使用旧 dist/binary。
- [ ] React 数据由真实 API 生成，不是静态关系或名称猜测；搜索、选择、重载、同名实体。
- [ ] 节点/边身份去重、未知/虚语义、递归环、局部展开/收起、请求/节点/边预算，拒绝全库载入。
- [ ] 点击节点/边：准确 index_id、实体、调用点、源码文件/行列/快照；切换 index_id 不混用旧请求/选择/源码。
- [ ] loading、空结果、API 错误、超时、网络失败和恢复状态；控制台无未处理错误。
- [ ] 尽可能使用真实 Chromium API/UI 对照；若无法执行，明确列为 BLOCKED/限制，不冒充 UI 通过。

## E. 工程与隐私

- [ ] 新依赖必要性、版本/锁文件、资源释放、架构重复、稳定文档和安装运行独立性。
- [ ] 不读取 RMC/reference/F11/真实私有或敏感文件；构建物/fixture/日志只在审核目录。
- [ ] `scripts/verify_m1.sh` 只能作为一项证据，另有自主反例和真实调用链证据。

## 判据

- P0：严重安全/破坏；P1：核心语义、数据一致性或必需功能；P2：重要鲁棒性、边界或必需 UI/API 行为；P3：局部改进。
- 关键验证未完成：BLOCKED；P0/P1 或必需 P2 失败：NEEDS_CORRECTION；只有合同、实证和候选身份均充分且无阻塞才 ACCEPT。
- 报告必须记录准确 argv、cwd、退出码、关键事实、失败与纠正；不得删除负面结果或放宽期待。
