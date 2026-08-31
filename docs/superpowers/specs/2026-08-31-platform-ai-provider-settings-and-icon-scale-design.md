# 平台 AI 服务参数配置与图标尺寸修正设计

## 背景

当前平台设置页只允许保存 API Key。API Key 会在服务端加密保存并在前端脱敏，但模型名和 Base URL 仍然直接读取部署环境变量，平台管理员无法在页面内配置完整的 OpenAI-compatible 服务连接参数。与此同时，AI 服务配置标题直接渲染 Element Plus 的原始 SVG，并传入了不适用于 SVG 的 `size` 属性，导致浏览器按默认尺寸拉伸，出现截图中的巨大图标。

## 目标与约束

- 平台管理员可以配置并保存 API Key、模型名称、Base URL。
- API Key 仍只在输入时提交；服务端只返回首尾 4 位掩码，不返回明文或密文。
- 首次配置必须提供 API Key；如果部署原本已有环境变量 API Key，首次保存模型名或 Base URL 时可留空并由服务端加密迁移该 Key。已有数据库配置再次保存时，API Key 留空表示保留原 Key，支持单独修改模型名或 Base URL。
- 模型名称和 Base URL 作为非敏感配置保存到同一条平台级配置记录，并由所有 AI worker 统一读取。
- 保留环境变量作为无数据库记录时的兼容回退；已有数据库记录中的空字段也回退到当前环境默认值，避免迁移后旧记录立即失效。
- Base URL 只接受 `http://` 或 `https://`，模型名不能为空；不在前端暴露任何敏感配置。
- AI 服务标题图标使用现有 Element Plus 图标容器，尺寸固定为 18px，与其他设置标题图标一致。

## 方案

### 数据与服务层

给 `PlatformAIConfiguration` 增加 `model` 和 `base_url` 字段。`ai_config.py` 暴露一个统一的运行时配置读取函数，返回解密后的 Key、有效模型名和有效 Base URL；只有调用 AI provider 的服务层能取得明文 Key，HTTP 响应继续使用 `get_ai_configuration_state()` 的安全元数据。

保存函数接收可选 API Key 与必填的模型名、Base URL：

1. 校验模型名非空且长度受限。
2. 校验 Base URL 的 scheme 为 HTTP 或 HTTPS，并限制长度。
3. 没有已有记录且请求没有 API Key 时，使用已有环境变量 Key 作为兼容回退并加密迁移；环境变量也为空时才要求 API Key。已有记录且 API Key 为空时保留已加密 Key。
4. 在事务中锁定默认记录并更新三个配置字段及审计操作者。

AI worker 的三条真实调用路径都改为读取同一个运行时配置，避免一部分任务仍使用 `settings.OPENAI_MODEL` 或 `settings.OPENAI_BASE_URL`。没有有效 API Key 时维持当前演示模式或可操作错误提示。

### HTTP API

`GET /api/platform-ai-config/` 返回：

```json
{
  "configured": true,
  "masked_key": "ark-********2b96",
  "model": "deepseek-v4-flash-260425",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3"
}
```

`PUT /api/platform-ai-config/` 接收：

```json
{
  "api_key": "可选；首次配置时必填",
  "model": "deepseek-v4-flash-260425",
  "base_url": "https://ark.cn-beijing.volces.com/api/v3"
}
```

接口只允许平台管理员访问；校验错误返回字段级 400，缺少加密密钥返回 503。响应始终不包含 `api_key` 或 `encrypted_api_key`。

### 前端交互

AI 配置卡片显示三个字段：密码类型 API Key、模型名称、Base URL。加载后显示当前掩码及非敏感参数。保存按钮提交三项配置；已配置状态下 Key 输入框为空仍允许保存另外两项。保存成功后清空 Key 输入框并保留返回的掩码。标题使用 `<el-icon :size="18">` 包裹 `Key`，避免原始 SVG 的默认尺寸。

## 错误处理

- 首次保存缺少 API Key 且部署没有环境变量回退：阻止保存并提示 API Key 必填。
- 已配置后 Key 为空：不改动原加密值。
- 模型名为空或 Base URL scheme 不合法：接口返回可读的字段错误，前端保留用户输入。
- 加密密钥缺失或格式错误：返回 503，不写入半成品配置。
- 旧记录的新增字段为空：运行时使用环境变量回退值，页面展示实际生效值。

## 测试策略

- 后端服务测试：保存模型与 Base URL、已有 Key 留空时保留 Key、首次保存仍要求 Key、无效 URL/空模型拒绝、数据库配置覆盖环境变量、AI worker 三条调用路径使用数据库参数。
- API 测试：平台管理员可读写安全元数据，非平台账号被拒绝，响应不包含明文或密文。
- 前端契约测试：接口类型和请求包含 `model`/`base_url`，页面渲染两个新输入并使用 18px 图标容器；Key 仍为 password 且不出现在响应类型中。
- 完成后运行完整后端测试、前端测试和构建，并刷新本地设置页验证掩码、字段值、保存交互和图标尺寸。

## 取舍

采用独立数据库字段而不是 JSON 配置列，因为字段职责清晰、校验直接、迁移后可查询且兼容当前单例记录。API Key 仍沿用现有 Fernet 加密方案，不将模型名或 Base URL 混入密文，以便安全地返回和编辑非敏感参数。
