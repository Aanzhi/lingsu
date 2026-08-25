# 灵溯全站研究工作台重设计实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 在不改变业务逻辑、接口协议、数据结构、权限和路由的前提下，把灵溯统一为易学、低认知负担的研究工作台，并将 AI 工作台收敛为学生能理解的四步流程。

**Architecture:** 以 frontend/src/lingsu-system.css 的语义令牌作为唯一视觉基础，以公共布局和页面骨架承载三端一致的信息层级。项目进度只使用现有 buildStepModels / buildChapters 展示模型；AI 保留现有对话、Agent 和生成接口，只重组展示状态、入口和确认写入流程。frontend/public/design-demo.html 是隔离的评审原型，不接入生产业务。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Vitest、Playwright、Django API（仅回归，不改协议）。

---

## 当前边界与不可变约束

- 保留所有现有公开 URL 和路由名称，不删除业务能力。
- 不修改 frontend/src/api.ts 的接口协议，不新增后端接口、数据库表或迁移。
- 不改变项目、任务、材料、审核、邀请、授权和 AI 对话的数据结构。
- 不覆盖工作区已有修改；每次只触碰本任务涉及的文件。
- 生产页面不引用 Demo 的静态数据；Demo 只用于评审设计方向。
- 全站所有项目进度使用五章节展示，22 个任务只在章节内部出现一次。
- 每个页面只有一个主要操作；每项能力只有一个主要入口。

## 页面信息架构

| 角色 | 一级入口 | 页面职责 |
| --- | --- | --- |
| 公共 | 入口、登录、注册、内容 | 解释平台、完成身份进入，不承载业务操作 |
| 学生 | 首页、我的项目、研究旅程、AI 助手 | 找到下一步、完成任务、查看项目证据 |
| 教师 | 工作台、项目池、指导项目、待审核 | 处理待办、指导项目、审核材料 |
| 平台 | 概览、学校空间、AI 模板、运营内容、设置 | 管理学校、模板和平台策略 |

---

### Task 1: 建立可回归的设计系统契约

**Files:**
- Modify: frontend/src/designSystemStyles.test.ts
- Modify: frontend/src/lingsu-system.css

- [ ] **Step 1: Write the failing tests**

在现有设计系统测试中新增以下断言，先描述目标契约：

~~~
it('uses one semantic surface, spacing and control contract', () => {
  for (const token of [
    '--surface-page', '--surface-card', '--surface-float',
    '--space-page', '--space-section', '--space-card', '--control-height',
    '--radius-sm', '--radius-md', '--color-primary-strong',
  ]) expect(styles).toContain(token)
})

it('provides one shared page shell and one primary action treatment', () => {
  expect(styles).toContain('.workspace-page')
  expect(styles).toContain('.workspace-page__header')
  expect(styles).toContain('.workspace-page__primary-action')
})
~~~

- [ ] **Step 2: Run the focused test and verify it fails**

Run:

~~~
cd frontend
npx vitest run src/designSystemStyles.test.ts
~~~

Expected: FAIL because the new semantic tokens and workspace shell selectors are not present.

- [ ] **Step 3: Implement the minimal token contract**

在 :root 增加别名令牌并让现有页面逐步复用：

~~~
:root {
  --surface-page: var(--color-bg-canvas);
  --surface-card: var(--color-bg-surface);
  --surface-float: var(--color-bg-surface);
  --space-page: clamp(16px, 3vw, 48px);
  --space-section: 24px;
  --space-card: 20px;
  --color-primary-strong: var(--moss-dark);
  --transition-fast: 160ms ease;
}

.workspace-page { width: 100%; max-width: var(--content-max); margin: 0 auto; }
.workspace-page__header { display: flex; align-items: flex-end; justify-content: space-between; gap: var(--space-5); margin-bottom: var(--space-section); }
.workspace-page__primary-action { flex: 0 0 auto; }
~~~

同时把新增渐变卡片替换为平面表面 + 边框，保留必要的进度条渐变。

- [ ] **Step 4: Run the focused test and the full unit suite**

Run:

~~~
cd frontend
npx vitest run src/designSystemStyles.test.ts
npm run test
~~~

Expected: new contract and all existing tests pass.

- [ ] **Step 5: Run whitespace validation**

Run git diff --check; expected no output.

---

### Task 2: 收敛公共布局和共享组件

**Files:**
- Modify: frontend/src/components/AppTopbar.vue
- Modify: frontend/src/components/PageHeader.vue
- Modify: frontend/src/components/Breadcrumbs.vue
- Modify: frontend/src/components/StatusTag.vue
- Modify: frontend/src/components/EmptyState.vue
- Modify: frontend/src/layouts/StudentLayout.vue
- Modify: frontend/src/layouts/TeacherLayout.vue
- Modify: frontend/src/layouts/PlatformLayout.vue
- Create: frontend/src/stores/navigationRegistry.ts
- Create: frontend/src/stores/navigationRegistry.test.ts

- [ ] **Step 1: Write the failing navigation contract test**

~~~
it('registers one primary entry per capability and role', () => {
  expect(primaryNavigation('student').map((item) => item.key))
    .toEqual(['home', 'projects', 'ai', 'content'])
  expect(primaryNavigation('teacher').map((item) => item.key))
    .toEqual(['home', 'pool', 'projects', 'reviews'])
  expect(primaryNavigation('platform_admin').map((item) => item.key))
    .toEqual(['home', 'schools', 'ai-agents', 'content'])
})

it('does not expose orphaned project or invitation entries in the primary nav', () => {
  const keys = primaryNavigation('student').flatMap((item) => item.children ?? [])
  expect(keys).not.toContain('invitations')
  expect(keys).not.toContain('public-applications')
})
~~~

- [ ] **Step 2: Run the focused test and verify it fails**

Run cd frontend && npx vitest run src/stores/navigationRegistry.test.ts; expected FAIL because the registry does not exist.

- [ ] **Step 3: Implement the registry and use it in layouts**

创建只负责展示注册表的 navigationRegistry.ts：

~~~
export type NavigationRole = 'student' | 'teacher' | 'platform_admin'
export interface NavigationItem {
  key: string
  label: string
  to: string
  children?: string[]
}
export function primaryNavigation(role: NavigationRole): NavigationItem[] {
  if (role === 'student') return [
    { key: 'home', label: '首页', to: '/student/home' },
    { key: 'projects', label: '我的项目', to: '/student/projects' },
    { key: 'ai', label: 'AI 助手', to: '/student/ai' },
    { key: 'content', label: '案例与赛事', to: '/student/cases' },
  ]
  if (role === 'teacher') return [
    { key: 'home', label: '工作台', to: '/teacher/home' },
    { key: 'pool', label: '项目池', to: '/teacher/pool' },
    { key: 'projects', label: '指导项目', to: '/teacher/projects' },
    { key: 'reviews', label: '待审核', to: '/teacher/reviews' },
  ]
  return [
    { key: 'home', label: '平台概览', to: '/platform/home' },
    { key: 'schools', label: '学校空间', to: '/platform/schools' },
    { key: 'ai-agents', label: 'AI 助手模板', to: '/platform/ai-agents' },
    { key: 'content', label: '赛事与公告', to: '/platform/competitions' },
  ]
}
~~~

布局只使用 registry 渲染一级导航；通知、邀请、成果申请、设置、案例和赛事保留 URL，但收进页面内的次级入口。补齐导航项的 aria-current、Tab 状态、Escape 关闭菜单和移动端横向滚动提示。

- [ ] **Step 4: 统一公共组件的 DOM 语义和状态**

PageHeader 输出统一的 .workspace-page__header；StatusTag 统一中文标签和非颜色图标；EmptyState 统一说明 + 下一动作；AppTopbar 的通知和帮助入口在移动端收进菜单，不直接 display:none。保留组件现有 props 和事件。

- [ ] **Step 5: Run focused tests and build**

Run:

~~~
cd frontend
npx vitest run src/stores/navigationRegistry.test.ts src/designSystemStyles.test.ts
npm run build
~~~

Expected: all pass.

---

### Task 3: 学生端项目、旅程和内容页面

**Files:**
- Modify: frontend/src/pages/student/StudentHome.vue
- Modify: frontend/src/pages/student/StudentProjects.vue
- Modify: frontend/src/pages/student/StudentProject.vue
- Modify: frontend/src/pages/student/StudentTask.vue
- Modify: frontend/src/pages/student/StudentInvitations.vue
- Modify: frontend/src/pages/student/PublicCaseApplication.vue
- Modify: frontend/src/pages/shared/ContentLibrary.vue
- Modify: frontend/src/components/JourneyTimeline.vue
- Modify: frontend/src/components/JourneyDeliveryBoard.vue
- Modify: frontend/src/stores/studentApiModel.ts
- Test: frontend/src/stores/studentApiModel.test.ts
- Test: frontend/src/journeyMapStyles.test.ts

- [ ] **Step 1: Add failing presentation assertions**

~~~
it('exposes exactly five chapter summaries for every project surface', () => {
  const models = buildChapters(buildStepModels(tasks))
  expect(models).toHaveLength(5)
  expect(models.flatMap((chapter) => chapter.tasks)).toHaveLength(tasks.length)
  expect(new Set(models.flatMap((chapter) => chapter.tasks.map((task) => task.id))).size)
    .toBe(tasks.length)
})
~~~

在样式测试中增加 workspace-chapter-list 和 768px 断言。

- [ ] **Step 2: Run the tests and verify the new assertions fail**

Run cd frontend && npx vitest run src/stores/studentApiModel.test.ts src/journeyMapStyles.test.ts; expected FAIL for the new selectors/model contract.

- [ ] **Step 3: Implement the student page hierarchy**

- StudentHome 只保留当前项目、下一行动、五章节摘要和必要通知。
- StudentProject 的概览、旅程、材料、报告 surface 都从同一章节模型读取。
- JourneyTimeline 只输出五章和章节进度。
- JourneyDeliveryBoard 输出折叠章节；当前章默认打开，完成/未开始默认收起。
- StudentTask 只保留一个“使用 AI 协助本任务”入口。
- 邀请、成果申请、案例/赛事/公告不进入学生一级导航，只保留明确的页面内入口或通知中心入口。

- [ ] **Step 4: Remove duplicate local presentation blocks**

删除页面内独立的 22 节点时间轴、重复材料列表和重复 AI 快捷按钮；不删除任务详情路由和数据。所有操作按钮使用既有 RouterLink/API 调用。

- [ ] **Step 5: Run focused student tests**

Run:

~~~
cd frontend
npx vitest run src/stores/studentApiModel.test.ts src/journeyMapStyles.test.ts src/journeyDeliveryMapping.test.ts
~~~

Expected: pass with five-chapter and responsive contracts.

---

### Task 4: 教师端项目池、指导详情和材料范本

**Files:**
- Modify: frontend/src/pages/teacher/TeacherWorkbench.vue
- Modify: frontend/src/pages/teacher/TeacherProjectDetail.vue
- Modify: frontend/src/pages/teacher/TeacherProjectTemplate.vue
- Modify: frontend/src/stores/teacherProjectModel.ts
- Test: frontend/src/teacherPoolStyles.test.ts
- Test: frontend/src/stores/teacherProjectModel.test.ts

- [ ] **Step 1: Write failing tests for the single-source detail model**

~~~
it('keeps teacher project rows free of duplicated detail fields', () => {
  const row = buildTeacherProjectRow(project)
  expect(row).toMatchObject({ title: project.title, ownerName: expect.any(String), memberCount: expect.any(Number) })
  expect(row).not.toHaveProperty('problem')
  expect(row).not.toHaveProperty('plan')
  expect(row).not.toHaveProperty('materials')
})
~~~

- [ ] **Step 2: Run the focused test and verify it fails**

Run cd frontend && npx vitest run src/stores/teacherProjectModel.test.ts; expected FAIL until the row model is introduced.

- [ ] **Step 3: Implement compact rows and five-chapter detail**

- TeacherWorkbench 的指导项目、归档、回收站共用同一行结构：名称、类型/状态、负责人、成员数、更新时间、唯一详情入口。
- TeacherProjectDetail 只展示项目摘要、五章节折叠区和右侧指导动作。
- TeacherProjectTemplate 直接加载教师项目和详情，复用章节模型；保留路由兼容。
- 章节标题使用 minmax(0, 1fr)，禁止 1280px 下单字竖排。
- 生命周期菜单桌面和移动端直接可见，Tab 补齐 aria-selected。

- [ ] **Step 4: Run teacher tests and check 1280/390 layouts**

Run:

~~~
cd frontend
npx vitest run src/stores/teacherProjectModel.test.ts src/teacherPoolStyles.test.ts
npm run build
~~~

Browser check at 390px and 1280px: no duplicated project fields, no vertical title collapse, one detail action per row.

---

### Task 5: 平台端学校、AI 模板和运营内容

**Files:**
- Modify: frontend/src/pages/platform/PlatformConsole.vue
- Modify: frontend/src/pages/platform/SchoolDetail.vue
- Modify: frontend/src/pages/platform/PlatformAIAgents.vue
- Modify: frontend/src/pages/platform/PlatformSettings.vue
- Modify: frontend/src/layouts/PlatformLayout.vue
- Test: existing platform style and model tests under frontend/src/*platform*test.ts

- [ ] **Step 1: Add failing page-contract assertions**

~~~
it('keeps school navigation separate from the authorization switch', () => {
  expect(consoleSource).toContain('查看详情')
  expect(consoleSource).toContain('aria-label')
  expect(consoleSource).not.toContain('<a')
})

it('provides AI template filters for name, role, group and status', () => {
  for (const field of ['模板名称', '角色', '分组', '状态']) expect(agentSource).toContain(field)
})
~~~

- [ ] **Step 2: Run focused tests and verify the new assertions fail**

Run the relevant Vitest files under frontend/src/platform*test.ts; expected FAIL for the missing page contracts.

- [ ] **Step 3: Implement the platform information hierarchy**

- PlatformConsole 只保留概览、学校、赛事和公告分支，旧的不可达分支不再渲染，但公开 URL 继续可访问。
- 学校列表把学校名称/查看详情和授权开关拆成两个独立控件；移动端变成摘要卡片。
- PlatformAIAgents 增加名称、角色、分组、启用状态筛选，窄屏使用局部滚动或卡片。
- PlatformSettings 只保留安全策略和服务健康信息，删除重复快捷导航。

- [ ] **Step 4: Run platform tests and build**

Run cd frontend && npm run test && npm run build; expected pass except existing dependency/chunk-size warnings.

---

### Task 6: AI 工作台逻辑收敛

**Files:**
- Modify: frontend/src/pages/shared/AICenter.vue
- Modify: frontend/src/stores/aiConversationModel.ts
- Modify: frontend/src/stores/presentationModel.ts
- Modify: frontend/src/stores/aiModel.ts
- Test: frontend/src/stores/aiConversationModel.test.ts
- Test: frontend/src/stores/presentationModel.test.ts
- Test: frontend/src/studentAICenterEntry.test.ts

- [ ] **Step 1: Write failing tests for the four-step state machine**

~~~
it('keeps AI research assistance in four student-readable steps', () => {
  expect(researchFlowStep(0)).toBe('goal')
  expect(researchFlowStep(1)).toBe('inputs')
  expect(researchFlowStep(2)).toBe('draft')
  expect(researchFlowStep(3)).toBe('confirm')
})

it('does not write an AI draft into a project before explicit confirmation', () => {
  expect(canWriteResearchDraft({ step: 'draft', confirmed: false })).toBe(false)
  expect(canWriteResearchDraft({ step: 'confirm', confirmed: true })).toBe(true)
})
~~~

- [ ] **Step 2: Run focused tests and verify they fail**

Run cd frontend && npx vitest run src/stores/aiConversationModel.test.ts src/stores/presentationModel.test.ts; expected FAIL until the pure helpers are added.

- [ ] **Step 3: Implement pure presentation/state helpers**

只增加前端展示状态，不改 API payload：

- 三个学生入口：找研究问题、完成当前任务、直接提问。
- Agent 列表、历史搜索、项目筛选和归档全部放到次级区域。
- 结构化结果统一成可编辑草稿；不完整结果保留原文并提示手动补齐。
- 只有确认按钮调用既有 createProject / 保存材料逻辑。
- 无真实模型时显示明确阻塞提示，不返回演示候选。

- [ ] **Step 4: Replace the AICenter template with the simplified hierarchy**

保留已有 SSE、重试、归档、重命名、材料保存和项目创建函数，只调整模板顺序、入口和状态展示；确保 aria-live、键盘焦点、Escape 关闭 Agent/历史面板和 prefers-reduced-motion。

- [ ] **Step 5: Run AI tests and build**

Run:

~~~
cd frontend
npx vitest run src/stores/aiConversationModel.test.ts src/stores/presentationModel.test.ts src/studentAICenterEntry.test.ts
npm run build
~~~

Expected: all pass and no API test snapshot changes.

---

### Task 7: 全量响应式、无障碍和回归验收

**Files:**
- Modify: frontend/e2e/mvp.spec.ts
- Modify: relevant page/style tests
- No backend files unless an existing test exposes a protocol regression

- [ ] **Step 1: Add failing E2E assertions**

~~~
test('core pages have one document width and one primary action at supported viewports', async ({ page }) => {
  for (const width of [390, 768, 1024, 1280, 1440]) {
    await page.setViewportSize({ width, height: 900 })
    await page.goto('/student/home')
    expect(await page.evaluate(() => document.documentElement.scrollWidth))
      .toBeLessThanOrEqual(await page.evaluate(() => window.innerWidth))
  }
})
~~~

Add checks for visible focus, aria-selected, Escape menu close, student AI single entry and teacher/platform no duplicate rows.

- [ ] **Step 2: Run the new E2E tests and verify the intended failures**

Run cd frontend && npm run test:e2e -- mvp.spec.ts; record failures caused by the new assertions before implementation.

- [ ] **Step 3: Fix responsive and accessibility regressions**

Check public, student, teacher and platform representative pages at 390px, 768px, 1024px, 1280px and 1440px. Fix shared layout/style causes first; do not add page-specific overrides unless the content genuinely differs.

- [ ] **Step 4: Run the complete verification set**

~~~
cd frontend
npm run test
npm run build
npm run test:e2e
git diff --check
cd ..
docker compose exec -T backend python manage.py test apps.core
~~~

Record existing dependency warnings separately from failures introduced by this work. Manually inspect browser console errors on public, student AI, student journey, teacher detail, platform schools and platform AI templates.

- [ ] **Step 5: Update the final report**

Report modified files, final token rules, page/entry consolidation, AI flow, viewport checks, commands and results, unchanged business behavior, and remaining risks. Do not mark the goal complete until every verification command and browser check has evidence.

---

## Commit / checkpoint order

Keep the dirty worktree intact and create reviewable checkpoints in this order:

1. test: add design system and navigation contracts
2. refactor: unify workspace shell and shared states
3. refactor: simplify student journey presentation
4. refactor: consolidate teacher project guidance views
5. refactor: streamline platform management surfaces
6. refactor: simplify student AI workbench flow
7. test: verify responsive and accessibility regression coverage

Do not commit unrelated existing changes. Before each checkpoint, run the focused tests named in that task and git diff --check.
