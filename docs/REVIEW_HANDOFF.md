# 未批准候选的只读交接

## 目的与权限

源码送审、研发验收、自动 Git 交付、main 合并和 Stable 晋升是不同动作。
`tools/review_handoff.py` 仅把已知身份的候选写入**本机审查包**，不要求 ACCEPT；
它不修改或读取审核状态库，不重置轮数、不触发模型、不执行候选代码、不调用 Git、
不上传文件，也不授予提交、推送、合并或 Stable 权限。旧 BLOCKED 原样保留。

这是外部操作者使用的独立工具，不是 Controller 交付 gate 的替代入口。
Linux/Python 3.10+；原生 Windows 暂不支持。工具应放在固定候选目录之外运行。

## 一次导出

从既有冻结记录中取得三项独立值，不要先对当前目录计算新哈希后当作已审核身份：
完整 manifest SHA-256、预期 Git tree SHA-1、文件数量。

```bash
python3 -B /path/to/review_handoff.py export \
  --source /absolute/frozen-candidate \
  --expect-sha256 <existing-candidate-sha256> \
  --expect-tree <existing-git-tree-sha1> \
  --expect-files <existing-file-count> \
  --output /private/existing-directory/source-review.zip
```

输出位置必须在候选目录外、父目录已存在且不是全局可写目录；文件以 0600 创建，
已有同名文件不覆盖。默认包含全部源码（含未跟踪或 ignored 文件），只忽略各层 `.git`，
与现有 `orchestration.common.manifest` 对齐。不执行源码以查询身份，也不隐式删减文件。

包中只有 `source/`、`manifest.json` 和 `handoff.json`。身份验证通过只产生：
`integrity=VERIFIED`、`review=NOT_PERFORMED`，所有执行/交付/晋升权限均为 false。
这不证明软件正确、测试通过或秘密扫描完整。

工具拒绝符号链接、硬链接、特殊文件、运行数据/凭据目录、疑似密钥、内容过滤器及
超出大小/数量/深度预算的候选。它不会用脱敏后的源码替换原字节并保留旧哈希。
发现疑似凭据时，应本地检查并另行处置；不能关闭原门禁或自动忽略该文件。
误报测试样本也会拒绝导出，不提供静默绕过。分享前仍须人工隐私检查。

## 接收方离线核验

```bash
python3 -B /path/to/review_handoff.py verify \
  --bundle /absolute/source-review.zip \
  --expect-sha256 <same-independent-candidate-sha256> \
  --expect-tree <same-independent-git-tree-sha1> \
  --expect-files <same-independent-file-count>
```

核验不解压、不执行任何包内内容；拒绝路径穿越、重复成员、伪造元数据、额外文件及
修改过的源码。依赖来自包外的已知身份，不把包自报的哈希当作真实性来源。
该版本输出 Git SHA-1 tree；不支持 SHA-256 object-format 仓库。

## 与整体验收收尾衔接

源码包到位后，读取原合同及原始审核裁决，把每个剩余阻塞具体化：

| 字段 | 必须记录的内容 |
|---|---|
| 合同原文与范围 | 原要求、哪份产品候选，不扩大或改写合同 |
| 具体缺口 | 代码缺陷／证据缺失／环境限制／人工决策，不能只写“未 ACCEPT” |
| 已有证据 | 路径、哈希、实际执行者、适用源码及明确限制 |
| 尚缺证据 | 可操作的步骤、期望观察和判定方式 |
| 身份分层 | 运行器候选、被开发的小任务候选、测试回执分别绑定 |
| 下一动作 | 定向补证或修复；原运行和已耗尽预算保持不变 |

源码交接不会关闭任何 finding。原始日志、用户会话、隐藏推理、凭据和私有访问 URL
不自动入包；确需审查的合同、裁决或截图由操作者另行选择并脱敏提供。报告中的
哈希只能绑定已有材料，不能代替材料本身。不要因为缺源码就启动新一轮模型重审。

工具测试：`python3 -B -m unittest discover -s tests -p test_review_handoff.py -v`。
Git tree 编码与 Git plumbing 对照，manifest 与已有源码快照函数对照；测试均不调用模型。
