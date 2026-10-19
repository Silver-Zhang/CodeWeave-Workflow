# 合同 Schema 与运行时门禁的边界

JSON Schema 2020-12 仅用于接口草案，尚未接入现有tools/devflower.py。examples中的会话/哈希均为明确示例，不是授权或审核证据；默认交付关闭。

workflow-policy不包含密钥、实际主机路径或会话UUID。绑定、批准配置哈希、远端和Controller版本由本地受信授权另存。timeout是运行预算示例，不是向用户承诺耗时。

review-result来自模型，不能自证可信。即使格式验证通过，Controller仍须检查：真实进程会话、run/round匹配、candidate/contract匹配、证据来自当前候选且实际执行、必需合同齐全且无重复、无矛盾ACCEPT、历史阻塞关闭、测试数量和skip有效、工作树/提交树一致以及Git权限。

特意允许Schema表达ACCEPT+FAIL等矛盾输入，以用于门禁负例；格式校验不能被当成通过门禁。所有路径/evidence_refs仅为标识；执行器按受信证据目录解析，绝不直接读取模型提供的任意本机路径或执行模型返回的shell命令。

适配器可以把供应商支持的Schema子集作为输出提示，但完整校验仍在Controller执行。已有角色/模式与任务状态不因这些Schema自动迁移。
