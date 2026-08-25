# 灵溯 Demo B 全站生产 UI 重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 以 `frontend/public/design-demo.html` 中 B「安静工作台」为唯一视觉母版，重新设计真实 Vue 生产项目的公共入口、学生端、教师端和平台端布局与 UI，使生产页面在结构、密度、卡片、列表、图标、配色、圆角、阴影、渐变和交互状态上与 Demo B 保持高还原度，同时保留现有业务协议、路由、权限和核心流程。

**Architecture:** 先把 Demo B 的视觉规则拆成生产级令牌、壳层和共享组件，再按角色迁移页面。学生端也采用 Demo B 的「66px 顶部品牌栏 + 232px 左侧工作区导航 + 内容区」结构；生产环境不带入 Demo 的角色切换器、方案切换器、评审提示条和静态模拟数据。页面数据继续来自现有 Pinia/API，AI 双路径和教师 AI 预审只做视觉与信息层级迁移，不改变协议。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Vitest、Playwright E2E。

**当前状态：** Task 1–9 已实施并完成最终全量回归。AI 服务未响应时，生产界面和 E2E 会明确报告阻塞，不会伪造结构化候选。

---

## 设计基准与不可变边界

### Demo B 必须复用的视觉规则

- 画布背景：`#F3F4F0`；卡片表面：`#FFFFFF`；次级表面：`#F8FAF7`；分组背景：`#EEF2ED`。
- 文字：主文字 `#1E2D26`、次文字 `#526159`、弱文字 `#829088`。
- 品牌：苔绿 `#4F6F59`、深苔绿 `#365440`、浅苔绿 `#E7F0E8`；强调色使用克制的陶土色 `#AD7953`。
- 顶栏 `66px`、桌面侧栏 `232px`、内容最大宽度 `1120px`、宽版审核/数据页 `1280px`。
- 卡片默认 `1px` 浅边框、`12px` 圆角、`0 2px 8px rgba(41,62,48,.05)` 阴影；只在悬浮和重要 Hero 使用更强阴影。
- 页面标题、章节标题、卡片标题、关键数字使用 `Georgia, "Songti SC", "STSong", "SimSun", serif`；正文、导航、表格、表单和按钮使用系统无衬线字体。
- 主按钮为苔绿色实心按钮；次按钮为白底浅边框；Subtle 按钮为透明文字按钮；状态使用浅背景胶囊，不使用大面积高饱和色块。
- 进度统一使用细圆角轨道；章节和材料使用圆形序号/文件图标底；列表使用分隔线和清晰的主次文本层级。
- 页面入口遵循「高频任务在主导航、低频页面收进更多；每页一个主要行动；同一能力只有一个主要入口」。
- Demo 顶部的 A/B/C 切换、角色切换、评审提示和静态数据只用于参考，不进入生产。

### 保持不变

- 不改后端 API、数据库、迁移、权限校验、公开路由 URL、项目数据结构和 AI 对话协议。
- 不删除已有课题创建、无课题 AI 引导、材料上传、版本提交、报告导出、教师审核、教师 AI 预审、学校授权和内容治理能力。
- 不把 Demo 模拟数据写入真实项目；不新增 UI 框架或重量级依赖。
- 工作区已有修改全部保留；不使用 `git reset --hard`、`git checkout --`、批量覆盖无关文件或清理用户修改。

## 生产页面与 Demo B 的职责对照

| Demo B 页面 | 真实生产页面 | 迁移重点 |
| --- | --- | --- |
| 学生端 · 今天 | `/student/home` | 顶栏 + 侧栏、深色研究 Hero、今日任务、五章节卡片、最近材料 |
| 我的项目 | `/student/projects` | 项目行/卡片、项目状态、唯一进入项目入口、双路径创建入口 |
| 项目概览 | `/student/projects/:id` | 项目摘要、五章节进度、下一行动、团队与风险 |
| 研究旅程 | `/student/projects/:id/map` | 五章节时间轴、折叠交付清单、当前章节突出 |
| 当前任务 | `/student/projects/:id/tasks/:taskId` | 任务侧栏、纸面编辑区、AI 辅助栏、提交状态 |
| 材料档案 | `/student/projects/:id/materials` | 按章节归档的材料列表、版本/审核状态 |
| 研究报告 | `/student/projects/:id/report` | 报告纸面、章节状态、导出条件和侧栏 |
| AI 助手 | `/student/ai` | 已有课题上下文、无课题四步引导、历史和工具抽屉 |
| 案例与赛事 | `/student/cases`、`/student/competitions`、`/student/announcements` | 内容卡片、搜索、空状态、唯一详情/报名操作 |
| 项目邀请/成果申请 | `/student/invitations`、`/student/public-applications` | 项目邀请只从顶栏通知中心进入；成果申请只从项目报告装配页的成果区进入，不进入侧栏 |
| 教师工作台 | `/teacher/home` | 指标卡、审核收件箱、下一指导动作 |
| 项目池/指导项目 | `/teacher/pool`、`/teacher/projects` | 项目摘要卡/紧凑行、认领与详情入口唯一 |
| 材料审核 | `/teacher/reviews`、`/teacher/reviews/:id` | 审核列表、纸面正文、附件、AI 预审、教师最终操作 |
| 项目详情/材料范本 | `/teacher/projects/:id`、`/teacher/projects/:id/template` | 五章节折叠、风险侧栏、唯一范本入口 |
| 平台概览/学校空间 | `/platform/home`、`/platform/schools`、`/platform/schools/:id` | 平台指标、学校授权分离、学校状态列表/移动卡片 |
| AI 助手模板/内容/设置 | `/platform/ai-agents`、`/platform/competitions`、`/platform/announcements`、`/platform/cases`、`/platform/settings` | 筛选表格、管理列表、状态和空状态统一 |
| 公共入口/登录/注册 | `/`、`/login`、`/register` | B 画布、品牌锁定、角色入口卡片、表单错误与移动布局 |

## 文件改造边界

### 公共壳层与视觉基础

- 修改：`frontend/src/layouts/StudentLayout.vue`、`TeacherLayout.vue`、`PlatformLayout.vue`。
  - 三端统一使用 Demo B 的顶部品牌栏和侧栏栅格。
  - 学生端从横向导航切换为 232px 左侧导航；主导航放今日旅程、我的项目、灵思 AI、案例与赛事；研究旅程、当前任务、材料档案、报告收进“更多页面”。项目邀请只从顶栏通知中心进入，成果申请只从项目报告装配页的成果区进入。
  - 侧栏图标统一为现有 Element Plus 图标，图标尺寸、间距、选中背景、焦点状态与 Demo B 的轻量导航一致。
- 修改：`frontend/src/components/AppTopbar.vue`。
  - 品牌标识、学校信息、通知、帮助、用户菜单重排为 Demo B 顶栏比例；品牌标记使用真实品牌字样，不带入 Demo 评审控件。
  - 保留通知加载、邀请跳转、帮助内容、退出登录和 Escape 关闭逻辑。
- 修改：`frontend/src/stores/navigationRegistry.ts`。
  - 增加角色侧栏的主导航/更多页面展示配置和 active 规则；不改变现有 route URL。
- 修改：`frontend/src/lingsu-system.css`、`frontend/src/styles/tokens.css`、`foundations.css`、`workspace.css`、`element-plus.css`、`responsive.css`。
  - 以 Demo B 的 CSS 规则为准，删除仍影响生产页面的旧间距、旧渐变、旧阴影、旧圆角和旧导航覆盖层。
  - 将卡片、列表、按钮、状态、表格、表单、对话框、抽屉、分页、加载、空状态和焦点环收敛到一套规则。
  - 860px 以下侧栏转为可横向浏览的工作区导航；390px 下保留核心入口和操作，不隐藏主要能力，不产生文档级横向滚动。

### 共享组件

- 修改：`PageHeader.vue`、`Breadcrumbs.vue`、`StatusTag.vue`、`EmptyState.vue`、`ConfirmDialog.vue`、`ProjectLifecycleMenu.vue`、`TaskStatusCard.vue`。
  - 页面标题统一为眉题、标题、说明、唯一主操作；状态标签统一图标/颜色/文案；空状态统一说明和下一步 CTA。
  - 统一菜单的 Escape、焦点、aria 状态和移动端可操作性。
- 修改：`JourneyHero.vue`、`JourneyTimeline.vue`、`JourneyDeliveryBoard.vue`。
  - 完全采用 Demo B 的深色 Hero、五章节圆形节点、折叠交付行和细进度轨道；继续使用既有 `buildStepModels`/`buildChapters` 数据。
- 保留并统一：`TeacherAIPreReview.vue`、`AIContextChooser.vue`、`AIResearchWizard.vue`、`AIConversationHistory.vue`、`AIToolPicker.vue`、`AIProjectAssistant.vue`。
  - AI 视觉表现为 Demo B 的纸面卡片和浅色提示块；AI 不自动创建空项目、不自动审核通过/退回。

## 分阶段实施任务

### Task 1：建立 Demo B 视觉验收基线

**Files:**

- Read-only reference: `frontend/public/design-demo.html`
- Create: `docs/superpowers/plans/2026-08-23-demo-b-reference-matrix.md`
- Test: `frontend/src/designDemo.test.ts`、`frontend/src/demoProductionParity.test.ts`

- [x] 记录 Demo B 学生首页、我的项目、研究旅程、当前任务、教师工作台、平台学校空间、公共入口在 1440px 和 390px 的截图与关键尺寸。
- [x] 在参考矩阵中明确每个生产页面必须复用的结构：顶栏高度、侧栏宽度、内容宽度、卡片间距、按钮层级、状态样式和移动策略。
- [x] 扩展测试，确保生产代码不导入 Demo 页面，不出现 Demo 角色/主题切换器，不出现 Demo 静态数据文案。
- [x] 运行 `cd frontend && npm run test -- --run src/designDemo.test.ts src/demoProductionParity.test.ts`，确认基线测试结果。

### Task 2：重做三端壳层与导航

**Files:**

- Modify: `frontend/src/layouts/StudentLayout.vue`
- Modify: `frontend/src/layouts/TeacherLayout.vue`
- Modify: `frontend/src/layouts/PlatformLayout.vue`
- Modify: `frontend/src/components/AppTopbar.vue`
- Modify: `frontend/src/stores/navigationRegistry.ts`
- Test: `frontend/src/stores/navigationRegistry.test.ts`、`frontend/e2e/mvp.spec.ts`

- [x] 将三个 Layout 改为 Demo B 的 `app-topbar + desk-shell + side-nav + desk-main` 结构。
- [x] 学生端侧栏加入主导航和“更多页面”，在有项目/无项目、当前项目详情和直接访问低频路由时都能生成有效链接；邀请和成果申请按业务上下文保留唯一入口。
- [x] 保证 active 状态只高亮当前职责入口；同一能力不同时出现在顶部、侧栏和页面主按钮中。
- [x] 运行 `cd frontend && npm run test -- --run src/stores/navigationRegistry.test.ts`。
- [x] 运行 E2E 中公共入口、学生、教师、平台导航场景，确认原路由和退出登录仍可用。

### Task 3：重做共享视觉基础

**Files:**

- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/foundations.css`
- Modify: `frontend/src/styles/workspace.css`
- Modify: `frontend/src/styles/element-plus.css`
- Modify: `frontend/src/styles/responsive.css`
- Modify: `frontend/src/components/PageHeader.vue`
- Modify: `frontend/src/components/Breadcrumbs.vue`
- Modify: `frontend/src/components/StatusTag.vue`
- Modify: `frontend/src/components/EmptyState.vue`
- Modify: `frontend/src/components/ConfirmDialog.vue`
- Modify: `frontend/src/components/ProjectLifecycleMenu.vue`
- Test: `frontend/src/designSystemStyles.test.ts`、`frontend/src/journeyTimelineStyles.test.ts`

- [x] 用 Demo B 的 `card`、`button`、`status`、`list-row`、`section-head`、`progress-track`、`callout` 和 `accordion` 结构替换生产中同职责但不同视觉的样式。
- [x] 把 Element Plus 输入框、选择器、开关、表格、分页、弹窗和下拉菜单映射到同一套 B 令牌；禁止用页面级 `!important` 堆叠覆盖。
- [x] 统一 loading/empty/error/disabled/hover/focus/selected 状态，并实现 `prefers-reduced-motion`。
- [x] 运行 `cd frontend && npm run test -- --run src/designSystemStyles.test.ts src/journeyTimelineStyles.test.ts`。

### Task 4：公共入口、登录和注册

**Files:**

- Modify: `frontend/src/pages/public/EntryPage.vue`
- Modify: `frontend/src/pages/public/LoginPage.vue`
- Modify: `frontend/src/pages/public/RegisterPage.vue`
- Modify: `frontend/src/pages/shared/ContentLibrary.vue`
- Test: `frontend/e2e/mvp.spec.ts`

- [x] 入口页使用 Demo B 的纸张画布、品牌锁定、左右分区和角色入口卡片；不加入营销 Hero、无意义渐变或模拟数据。
- [x] 登录/注册沿用真实认证、邀请码、错误和角色跳转，只重做表单容器、字段间距、按钮、错误反馈和窄屏布局。
- [x] 案例/赛事/公告复用 Demo B 的内容卡片、筛选栏和空状态；学生、教师、平台权限操作保持原逻辑。
- [x] 验证匿名入口、登录、注册和角色跳转。

### Task 5：学生端页面重做

**Files:**

- Modify: `frontend/src/pages/student/StudentHome.vue`
- Modify: `frontend/src/pages/student/StudentProjects.vue`
- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/pages/student/StudentTask.vue`
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/pages/student/StudentInvitations.vue`
- Modify: `frontend/src/pages/student/PublicCaseApplication.vue`
- Modify: `frontend/src/components/ai/AIContextChooser.vue`
- Modify: `frontend/src/components/ai/AIResearchWizard.vue`
- Modify: `frontend/src/components/ai/AIConversationHistory.vue`
- Modify: `frontend/src/components/ai/AIToolPicker.vue`
- Test: `frontend/src/aiCenterUI.test.ts`、`frontend/src/studentAICenterEntry.test.ts`、`frontend/e2e/mvp.spec.ts`

- [x] 首页按 Demo B 重排为页面标题、深色研究 Hero、今日任务白卡、五章节网格、最近材料和研究提醒。
- [x] 项目书架改为 Demo B 的紧凑项目列表/纸面卡片；管理菜单直接可见；保留“已有课题直接填写”和“无课题 AI 引导”两个明确入口。
- [x] 项目详情、研究旅程、材料档案和报告装配统一为五章节信息模型，删除 22 个任务的重复展示；交付清单只保留一个权威入口。
- [x] 当前任务使用 Demo B 的三栏纸面布局：任务侧栏、编辑纸面、AI 辅助卡；一个主要 AI 入口，快捷能力收进次级区域。
- [x] AI 首屏区分已有课题/无课题；无课题按“发现现象 → 打开问题 → 头脑风暴 → 共同成题”推进，确认前不调用创建项目；已有课题只读取当前项目上下文。
- [x] 历史对话、Agent 搜索/筛选、报告不可导出状态、邀请和成果申请使用统一卡片和抽屉，不增加重复主导航入口。
- [x] 验证已有课题创建、无课题 AI 引导、项目旅程、任务提交、材料档案、报告导出条件和 AI 对话状态。

### Task 6：教师端项目、审核和 AI 预审

**Files:**

- Modify: `frontend/src/pages/teacher/TeacherWorkbench.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectDetail.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectTemplate.vue`
- Modify: `frontend/src/components/TeacherAIPreReview.vue`
- Test: `frontend/src/teacherAIReviewUI.test.ts`、`frontend/src/teacherPoolStyles.test.ts`、`frontend/e2e/mvp.spec.ts`

- [x] 工作台使用 Demo B 的指标卡、审核收件箱和优先处理区；指标只承担导航，不制造重复操作入口。
- [x] 项目池使用纸面项目卡，突出研究问题摘要、学生、状态和唯一认领操作；指导项目/归档/回收站使用相同紧凑列表结构。
- [x] 项目详情只展示五章节折叠结构、团队/风险侧栏和章节内材料；移除 22 条阶段与 22 条材料的并列重复区块。
- [x] 审核详情按正文、附件、AI 预审、教师评语、最终决定顺序呈现；AI 只能生成检查建议和评语草稿，不能自动通过、退回或解锁。
- [x] 材料范本只从项目详情提供一个入口；直接访问模板页时补齐项目加载和返回路径。
- [x] 验证教师项目池、指导项目、项目详情、AI 预审、审核通过/退回、成员确认和材料范本。

### Task 7：平台端页面和管理入口

**Files:**

- Modify: `frontend/src/pages/platform/PlatformConsole.vue`
- Modify: `frontend/src/pages/platform/PlatformAIAgents.vue`
- Modify: `frontend/src/pages/platform/SchoolDetail.vue`
- Modify: `frontend/src/pages/platform/PlatformSettings.vue`
- Modify: `frontend/src/pages/platform/PlatformCases.vue`
- Test: `frontend/src/platformLicenseStyles.test.ts`、`frontend/e2e/mvp.spec.ts`

- [x] 平台概览使用 Demo B 的指标卡、学校授权健康列表和内容概览卡；不保留不可达旧分支或重复快捷导航。
- [x] 学校列表将详情链接与授权开关彻底分离；邀请码使用稳定代码块；移动端使用可读卡片而非整页横向表格。
- [x] AI 助手模板提供名称、角色、分组、启用状态搜索/筛选；桌面为 B 风格表格，移动为 B 风格卡片。
- [x] 学校详情、案例、赛事、公告、设置统一使用 B 卡片、列表、状态和弹窗；现有授权/内容 API 不变。
- [x] 验证平台概览、学校授权、学校详情、AI 模板筛选、内容发布/撤回和设置页。

### Task 8：逐屏视觉对照与响应式收敛

**Files:**

- Modify: all production style/page files identified by screenshot comparison
- Test: `frontend/e2e/mvp.spec.ts`、`frontend/src/demoProductionParity.test.ts`
- Create: `docs/superpowers/plans/2026-08-23-demo-b-visual-qa.md`

- [x] 在 1440px、1280px、1024px、768px、390px 逐页捕获 Demo B 参考状态和真实生产状态。
- [x] 每次对照检查：顶栏/侧栏比例、内容宽度、标题位置、卡片高度、列数、间距、按钮层级、状态胶囊、图标尺寸、阴影、圆角、文字截断和滚动行为。
- [x] 修复所有 P0/P1 视觉差异：学生侧栏缺失、旧布局残留、标题竖排、重复入口、文档级溢出、移动端核心操作隐藏。
- [x] 检查键盘焦点、Escape 关闭菜单/弹窗、Tab `aria-selected`、开关语义、状态不只依赖颜色和 reduced motion。
- [x] 视觉 QA 文档记录每个页面的最终状态和遗留限制；只有同视口对照通过后才进入最终验证。

### Task 9：完整回归与交付

**Files:**

- Test: `frontend` and relevant `backend` test suites
- Review: `git diff --check`

- [x] 运行 `cd frontend && npm run test`，期望所有 Vitest 文件通过。
- [x] 运行 `cd frontend && npm run build`，期望 `vue-tsc` 与 Vite 构建通过；依赖注释或 chunk size 仅作为已有警告记录。
- [x] 运行 `cd frontend && npm run test:e2e`，期望公共入口、三端核心流程、AI 双路径、教师 AI 预审和五种视口通过。
- [x] 运行相关 Django 测试：`cd backend && python manage.py test apps.core.tests.test_ai_conversations apps.core.tests.test_ai_service apps.core.tests.test_agents apps.core.tests.test_project_lifecycle -v 2`，确认无后端回归。
- [x] 运行 `git diff --check`，确认无空白错误。
- [x] 最终报告列出修改文件、Demo B 还原点、公共入口新增/调整、AI/业务保持不变项、命令结果、浏览器检查页面/视口和剩余风险。

## 检查点与停止条件

1. **壳层检查点：** 三端真实页面都已出现 Demo B 的顶栏、侧栏、内容画布和导航层级；在此之前不进入逐页装饰。
2. **学生核心检查点：** `/student/home`、`/student/projects`、`/student/projects/:id/map`、`/student/ai` 与 Demo B 同视口对照通过；确认后继续教师/平台页面。
3. **全站检查点：** 公共入口、学生、教师、平台主要页面均完成结构迁移，重复入口和旧样式残留清理。
4. **完成条件：** 视觉对照、功能回归、响应式、无障碍、单元测试、构建、E2E、后端相关测试和差异检查全部如实通过；不能因为某些页面“已经改善”而提前结束。
