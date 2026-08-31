# 灵思 AI 工作台重设计 Implementation Plan

> For agentic workers: implement this plan task-by-task. Steps use checkbox syntax for tracking.

Goal: 将学生端灵思 AI 收敛为与已确认线框一致的三模式聊天工作台，消除模式、Agent、上下文和聊天区域之间的层级冲突，同时保留真实会话、流式生成、开题确认和材料草稿能力。

Architecture: AICenter.vue 负责路由上下文、会话状态和两种页面状态；新建态与聊天态共享一个 AIWorkbenchComposer，通过根状态 class 控制布局。平台 AI 模板只在状态层自动解析，不在学生页面展示。AIResultCard.vue 仅承载需要确认的结构化结果。所有改动避让工作区现有未提交修改。

Tech Stack: Vue 3、TypeScript、Vue Router、Element Plus、Vite、Vitest。

---

## Task 1: 固化批准的页面契约与定向测试

- [ ] 在 AI 页面测试中增加断言：新建态有三模式、轻量意图入口和单一 Composer；不渲染 Agent、工具搜索、材料引用、前置填空或旧空白欢迎区。
- [ ] 增加断言：聊天态使用单一消息流和固定 Composer，隐藏模式区；普通消息不依赖厚重结果卡。
- [ ] 增加结果卡断言：界面显示用户语言的结果标题，不直接显示平台模板技术名。
- [ ] 运行 AI 相关 Vitest，确认新增断言在生产代码修改前能够识别当前差异。

## Task 2: 重组 AICenter 两种状态

- [ ] 增加按模式返回的三个快捷意图和“填入 Composer”行为，不把意图扩展为表单。
- [ ] 将新建态改为标题、模式、意图和 Composer 的单一垂直结构；研究/成果表达只显示自动绑定的只读项目标签。
- [ ] 将聊天态改为轻量顶栏、最大化消息流和底部 Composer，确保一个页面只有一个 Composer。
- [ ] 保留懒创建会话、真实流式状态、停止、重试、刷新恢复和开题/材料写入回调。
- [ ] 保持历史入口只在新建态可见，继续复用现有历史组件和会话接口。

## Task 3: 收敛结果卡的视觉层级

- [ ] 移除结果卡中的技术 Agent 名称和“灵思 AI 生成结果”式冗余标题。
- [ ] 将普通研究/成果结果改为紧凑编辑区域；仅在结果存在时显示操作。
- [ ] 保留复制、重新生成、保存草稿、开题编辑和二次确认创建项目。

## Task 4: 统一学生侧文案入口

- [ ] 将学生导航中的“赛事信息”改为“平台通知”，保持实际路由和通知数据不变。
- [ ] 检查 AI 页面和导航不重新引入旧宣传文案、技术 Agent 展示和重复入口。

## Task 5: 定向验收

- [ ] 运行 npm --prefix frontend test -- --run src/aiCenterUI.test.ts src/aiWorkbenchLayout.test.ts src/studentAICenterEntry.test.ts src/aiResultCard.test.ts。
- [ ] 运行 npm --prefix frontend run build。
- [ ] 对 1280px 和 1440px 页面做浏览器检查：新建态与聊天态无横向滚动，聊天态仅消息区滚动，输入框固定在底部。
- [ ] 运行 git diff --check。
- [ ] 本轮不运行全站 E2E；只有定向验收失败时再扩大检查范围。

## 回归边界

- 不修改后端接口、数据库模型、教师审核业务和部署配置。
- 不删除历史会话数据、AI 日志或材料引用能力；仅收敛学生端展示入口。
- 不使用子代理，不执行会覆盖现有修改的 Git 操作。
