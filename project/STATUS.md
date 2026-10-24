# 当前状态

当前任务20261024_06_main-stable-integration：按用户明确决定完成PR15/17人工集成、分支收尾、main同步和固定日常版启用。当前使用指南见本任务使用指南.md；历史任务05/04不改写。

main=bedee3229e0c4420c9112a5b62eac9a0e81d6458，tree=2e3c444f036e6f2e02bfcddd8301a5f0b1cd8e79，CF=7b0c0b3bcc95235e02eadb74b71dd5f50d3d9c88da178b4787ff2090d1978210/175文件。本地只保留main 和 project/devflower，云端另保留project/codeweave，开发分支已删、原worktree/会话不删。records已普通merge采用main并更新framework_base。

本轮重跑547Python、6host、165ChromiumHTTP、20JS及baseline/6语法均0FAIL/ERROR/SKIP。最终main与实际测试head27864fc的完整tree/CF相同；在main另跑baseline和6host通过。

日常入口：python3 /home/workspace/DevFlower/.local/open-devflower.py；固定副本stable/main-7b0c0b3bcc95，实际HTTP200，原storage/native路径不变。旧open-stable/open-workbench/open-model-admission入口转同一入口，原脚本和旧Stable5816留本地备份。

重要边界：人工合并不改写技术裁决。原Claude/Gate仍BLOCKED（两个P1 CLOSED，真实顺序超时、汇合未补证）。v3仍显示Development/可信Stable标记false；没有伪造ACCEPT或正式晋升TrustedRelease。当前自动业务交付配置为空，用户本人UX验收未进行。
