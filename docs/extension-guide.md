# Extension Guide

## 接入模型

实现 `LLMClient` 协议，并将实例注入自定义 Stage。模型输出必须先经过结构化解析和 Pydantic 校验，不能直接进入发布包。

## 新增行业模板

1. 在 `examples/` 增加请求样本。
2. 新增行业专用问题树和假设生成函数。
3. 加入对应 Golden Cases。
4. 设置独立质量阈值。
5. 在 CI 中构建并验证示例包。

## 适配工具系统

每个工具必须有：

- 输入和输出 Schema
- 最小权限说明
- 超时和重试策略
- 错误分类
- 降级行为
- 写操作审批
- 审计事件

## 发布流程

建议环境：`draft → pilot → production`。

只有真实评估达到阈值、Owner 已指定、安全评审通过后，才允许设置 `production-ready`。
