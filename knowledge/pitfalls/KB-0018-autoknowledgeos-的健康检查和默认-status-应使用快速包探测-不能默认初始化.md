# AutoKnowledgeOS 的健康检查和默认 status 应使用快速包探测，不能默认初始化外部 SDK 客户端；需要真实客户端初始化时应显式运行 status --deep。

- id: 18
- type: pitfall
- scope: repository
- status: published
- source_task: TASK-20260804-212659-升级-preflight-v2-高级知识闭环
- tags: status,health-check,external-sdk,fast-probe,deep-check
- created_at: 2026-08-04T22:13:01
- published_at: 2026-08-04T22:13:52

## Evidence

2026-08-04: 完整体检和 status 曾因外部适配器初始化卡住；修复 adapters.py 增加 probe_adapter_statuses 与 AUTO_KB_DISABLE_EXTERNAL，cli status 默认 fast，status --deep 才初始化真实适配器；单元测试 10/10 和 full-auto-audit pass true。

## Conclusion

AutoKnowledgeOS 的健康检查和默认 status 应使用快速包探测，不能默认初始化外部 SDK 客户端；需要真实客户端初始化时应显式运行 status --deep。
