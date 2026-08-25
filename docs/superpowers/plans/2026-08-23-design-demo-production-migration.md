# 灵溯 UI Demo 生产迁移 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 `frontend/public/design-demo.html` 已确认的信息架构、视觉语言和交互逻辑迁入真实 Vue 项目，使公共入口、学生端、教师端和平台端都使用真实 API、权限、路由和状态完成业务闭环。

**Architecture:** Demo 只作为视觉和交互验收基准，不被生产代码 import，也不复制其中的静态数据。生产页面继续使用现有 Vue 3、Element Plus、Pinia、Vue Router 和 Django API；迁移顺序为公共契约 → 学生核心闭环 → AI 工作台 → 教师审核 → 平台端 → 删除旧实现 → 全量回归。已完成的五章节模型、双路径项目创建、紧凑教师项目行和平台筛选直接保留，只修正与 Demo 仍不一致的部分。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Vitest、Playwright、Django REST Framework。

---

## 迁移边界

- 保留所有现有公开 URL、API 字段、数据库结构和权限逻辑。
- 不把 Demo 的模拟数据、toast 行为、角色切换器或三套主题切换器带入生产。
- 生产只保留一套已确认的“安静研究工作台”视觉基线：象牙白/纸张表面、苔绿色主色、克制边框和阴影。
- 已登录用户访问 `/` 时仍自动进入对应角色首页；未登录用户访问 `/` 时展示品牌入口，再进入登录或注册。
- AI 未配置时显示真实阻塞提示，不返回演示候选。
- 教师 AI 只生成预审建议和评语草稿，不自动通过、退回或解锁任务。
- 当前工作区包含用户已有修改；执行时只编辑本计划列出的文件，不 reset、checkout 或批量覆盖。
- 当前工作区较脏，执行阶段以测试检查点代替自动提交；只有用户明确要求时才创建提交。

## 当前差距结论

| 模块 | 当前状态 | 本轮动作 |
| --- | --- | --- |
| 五章节旅程 | 已进入生产 | 保留模型，只统一展示和筛选 |
| 新建项目双路径 | 已进入生产 | 补齐从入口到真实项目的端到端验收 |
| 学生 AI | 功能已进入生产，但 `AICenter.vue` 仍有 867 行和三段叠加样式 | 拆成任务导向组件，历史与工具降为次级入口 |
| 教师项目列表/详情 | 主结构已进入生产 | 补齐 AI 建议写入评语草稿和页面拆分 |
| 平台学校/AI 模板 | 主结构已进入生产 | 收敛筛选、移动端和内容页面样式 |
| 公共入口 | `/` 仍是加载跳转页 | 未登录时迁移 Demo 品牌入口 |
| 全局样式 | `lingsu-system.css` 超过 1000 行 | 完成页面迁移后按职责拆分并删除失效选择器 |
| 旧组件 | 多个组件已无生产引用 | 全量回归后删除，避免继续叠加 |

## 路由验收矩阵

| Demo 页面 | 生产路由 | 真实数据来源 | 主要操作 |
| --- | --- | --- | --- |
| 品牌入口 | `/` | 登录状态 | 登录工作台 |
| 登录/注册 | `/login`、`/register` | auth API | 登录或创建账号 |
| 学生首页 | `/student/home` | projects/tasks/notifications | 开始当前任务 |
| 我的项目/创建项目 | `/student/projects` | projects API | 新建或进入项目 |
| 研究旅程 | `/student/projects/:id/map` | project-tasks API | 打开当前任务 |
| 当前任务 | `/student/projects/:id/tasks/:taskId` | task/material API | 保存并提交 |
| 材料档案 | `/student/projects/:id/materials` | materials API | 打开材料 |
| 研究报告 | `/student/projects/:id/report` | report API | 条件满足后导出 |
| 学生 AI | `/student/ai` | AI conversations/agents | 当前项目辅助或无课题引导 |
| 教师工作台/项目池/项目 | `/teacher/home`、`/teacher/pool`、`/teacher/projects` | teacher project API | 认领或查看详情 |
| 教师项目详情 | `/teacher/projects/:id` | project/tasks/materials | 进入章节或审核 |
| 材料审核/AI 预审 | `/teacher/reviews`、`/teacher/reviews/:submissionId` | revisions/AI generation | 教师通过或退回 |
| 材料范本 | `/teacher/projects/:id/template` | task templates | 保存范本 |
| 平台概览/学校 | `/platform/home`、`/platform/schools`、`/platform/schools/:id` | platform API | 查看或切换授权 |
| AI 模板 | `/platform/ai-agents` | agents API | 新建或编辑模板 |
| 赛事/公告/案例 | 各角色现有内容路由 | content API | 按权限查看或管理 |
| 平台设置 | `/platform/settings` | service status API | 查看策略与健康状态 |

---

### Task 1: 建立 Demo 到生产的回归契约

**Files:**
- Create: `frontend/src/demoProductionParity.test.ts`
- Modify: `frontend/src/designSystemStyles.test.ts`
- Modify: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 写入路由和职责契约测试**

在 `demoProductionParity.test.ts` 中创建以下测试，先让它因缺少迁移标记而失败：

```ts
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const router = readFileSync(new URL('./router.ts', import.meta.url), 'utf8')
const aiCenter = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')
const entry = readFileSync(new URL('./pages/public/EntryPage.vue', import.meta.url), 'utf8')
const teacherReview = readFileSync(new URL('./pages/teacher/TeacherWorkbench.vue', import.meta.url), 'utf8')
const teacherAI = readFileSync(new URL('./components/TeacherAIPreReview.vue', import.meta.url), 'utf8')

describe('design demo production parity', () => {
  it('keeps every approved surface on a real production route', () => {
    for (const routeName of [
      'student-projects', 'student-ai', 'teacher-projects',
      'teacher-reviews', 'platform-schools', 'platform-ai-agents',
    ]) expect(router).toContain(`name: '${routeName}'`)
  })

  it('exposes the two student AI contexts without creating an empty project', () => {
    expect(aiCenter).toContain('我已有项目课题')
    expect(aiCenter).toContain('我还没有项目课题')
    expect(aiCenter).toContain('确认并生成项目前不会创建空项目')
  })

  it('gives anonymous users a real brand entry', () => {
    expect(entry).toContain('从一个好问题开始')
    expect(entry).toContain('登录工作台')
  })

  it('keeps teacher AI review advisory', () => {
    expect(teacherReview).toContain('TeacherAIPreReview')
    expect(teacherAI).toContain('仍由教师决定')
  })
})
```

- [ ] **Step 2: 运行测试确认 RED**

Run:

```bash
cd frontend
npx vitest run src/demoProductionParity.test.ts
```

Expected: `gives anonymous users a real brand entry` 失败，其余断言用于锁定已完成能力。

- [ ] **Step 3: 扩展 E2E 迁移矩阵**

在 `e2e/mvp.spec.ts` 增加一个数据驱动页面检查，使用现有 `login()`，不硬编码项目 ID：

```ts
test('Demo 对应的生产页面都能通过真实路由访问', async ({ page }) => {
  const surfaces = [
    ['student', '/student/home', '今天'],
    ['student', '/student/projects', '项目书架'],
    ['student', '/student/ai', '先说清楚你现在需要什么'],
    ['teacher', '/teacher/home', '指导工作台'],
    ['teacher', '/teacher/projects', '指导项目'],
    ['teacher', '/teacher/reviews', '学生材料审核'],
    ['platform_admin', '/platform/home', '平台概览'],
    ['platform_admin', '/platform/schools', '学校与邀请码'],
    ['platform_admin', '/platform/ai-agents', 'AI 助手模板'],
  ] as const

  for (const [role, path, text] of surfaces) {
    await page.context().clearCookies()
    await login(page, role, path)
    await expect(page.getByText(text, { exact: false }).first()).toBeVisible()
  }
})
```

- [ ] **Step 4: 保留基线输出**

Run:

```bash
cd frontend
npx vitest run src/designSystemStyles.test.ts src/demoProductionParity.test.ts
```

Expected: 只保留 Task 2 尚未实现的公共入口失败，已落地能力保持通过。

---

### Task 2: 将公共入口和认证页迁移为真实生产页面

**Files:**
- Modify: `frontend/src/pages/public/EntryPage.vue`
- Modify: `frontend/src/pages/public/LoginPage.vue`
- Modify: `frontend/src/pages/public/RegisterPage.vue`
- Modify: `frontend/src/lingsu-system.css`
- Test: `frontend/src/demoProductionParity.test.ts`
- Test: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 改造 EntryPage 的状态模型**

`EntryPage.vue` 使用下面的脚本结构：已登录立即按角色跳转，未登录停止 loading 并展示入口。

```ts
const router = useRouter()
const restoring = ref(true)

onMounted(async () => {
  const user = await auth.restore()
  if (user) {
    await router.replace(routeForAuthRole(user.role))
    return
  }
  restoring.value = false
})
```

- [ ] **Step 2: 迁移公共入口 DOM**

`EntryPage.vue` 的未登录模板使用真实 RouterLink，不使用 Demo toast：

```vue
<main v-if="!restoring" class="public-entry">
  <header class="public-entry__nav">
    <div class="auth-brand"><span class="brand-mark">S</span><strong>灵溯</strong></div>
    <div class="public-entry__actions">
      <RouterLink class="secondary-button" to="/login">登录</RouterLink>
      <RouterLink class="primary-button" to="/register">使用邀请码注册</RouterLink>
    </div>
  </header>
  <section class="public-entry__hero">
    <div>
      <p class="eyebrow">灵溯 · 青少年科学创新项目工作台</p>
      <h1>从一个好问题开始。</h1>
      <p>把课题、研究过程、材料证据和成果报告组织成一条清晰的研究旅程。</p>
      <RouterLink class="primary-button" to="/login">登录工作台 →</RouterLink>
    </div>
    <ol class="public-entry__journey" aria-label="五章研究旅程">
      <li><span>01</span><strong>问题提出</strong></li>
      <li><span>02</span><strong>资料查找</strong></li>
      <li><span>03</span><strong>方案设计</strong></li>
      <li><span>04</span><strong>实践验证</strong></li>
      <li><span>05</span><strong>成果表达</strong></li>
    </ol>
  </section>
</main>
<div v-else class="entry-loader" aria-label="正在进入灵溯">
  <span class="brand-mark">S</span><p>正在进入灵溯…</p>
</div>
```

- [ ] **Step 3: 收敛登录和注册页**

保留现有 auth API、校验、redirect 参数和开发环境演示账号，仅把两页的顶部文案、表单间距、错误状态和移动端布局改为与公共入口共用的 `.auth-page`、`.auth-card`、`.form-error` 契约。注册角色按钮补充：

```vue
<button
  type="button"
  role="tab"
  :aria-selected="form.role === 'student'"
  :class="{ active: form.role === 'student' }"
  @click="form.role = 'student'"
>我是学生</button>
```

- [ ] **Step 4: 验证公共入口**

在 `mvp.spec.ts` 增加匿名入口测试：

```ts
test('未登录用户先看到品牌入口', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '从一个好问题开始。' })).toBeVisible()
  await page.getByRole('link', { name: /登录工作台/ }).click()
  await expect(page).toHaveURL(/\/login$/)
})
```

Run:

```bash
cd frontend
npx vitest run src/demoProductionParity.test.ts
npm run build
npx playwright test e2e/mvp.spec.ts --grep "公共入口|Demo 对应"
```

Expected: 匿名 `/` 展示入口；已登录 `/` 跳转角色首页；登录、注册和返回链接可操作。

---

### Task 3: 完成学生端 Demo 与真实业务闭环的页面对齐

**Files:**
- Modify: `frontend/src/pages/student/StudentHome.vue`
- Modify: `frontend/src/pages/student/StudentProjects.vue`
- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/pages/student/StudentTask.vue`
- Modify: `frontend/src/components/JourneyTimeline.vue`
- Modify: `frontend/src/components/JourneyDeliveryBoard.vue`
- Modify: `frontend/src/stores/studentApiModel.ts`
- Test: `frontend/src/stores/studentApiModel.test.ts`
- Test: `frontend/src/journeyDeliveryMapping.test.ts`
- Test: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 锁定学生页面的唯一主操作**

在 `studentApiModel.test.ts` 增加展示决策测试：

```ts
it('selects one primary student action from the current project state', () => {
  expect(studentPrimaryAction({ currentTaskId: 8, projectId: 3, reportReady: false }))
    .toEqual({ label: '开始当前任务', to: '/student/projects/3/tasks/8' })
  expect(studentPrimaryAction({ currentTaskId: null, projectId: 3, reportReady: true }))
    .toEqual({ label: '查看研究报告', to: '/student/projects/3/report' })
})
```

在 `studentApiModel.ts` 实现：

```ts
export function studentPrimaryAction(input: {
  currentTaskId: number | null
  projectId: number
  reportReady: boolean
}) {
  if (input.currentTaskId) return {
    label: '开始当前任务',
    to: `/student/projects/${input.projectId}/tasks/${input.currentTaskId}`,
  }
  return input.reportReady
    ? { label: '查看研究报告', to: `/student/projects/${input.projectId}/report` }
    : { label: '打开研究旅程', to: `/student/projects/${input.projectId}/map` }
}
```

- [ ] **Step 2: 对齐学生首页和项目书架**

- `StudentHome.vue` 只展示当前项目、当前章、下一任务、最近材料和一条研究提醒。
- `StudentProjects.vue` 保留“已有课题”和“还没有课题”两条真实创建路径；已有课题调用现有 `createProject`，无课题只跳 `/student/ai?mode=brainstorm&agent=proposal-topic`。
- 列表中的进入项目、归档、回收站使用现有路由和生命周期 API，不增加 Demo 操作。

学生首页主操作只从 `studentPrimaryAction()` 输出：

```vue
<RouterLink class="primary-button" :to="primaryAction.to">
  {{ primaryAction.label }} →
</RouterLink>
```

- [ ] **Step 3: 对齐旅程、材料和报告**

所有页面继续使用 `buildStepModels()` 和 `buildChapters()`：

```ts
const stepModels = computed(() => buildStepModels(tasks.value))
const chapters = computed(() => buildChapters(stepModels.value))
```

- 旅程只显示五章；当前章默认展开。
- 材料按五章分组，并新增纯前端关键词、章节和状态筛选，不新增 API。
- 报告从已审核材料装配；不满足条件时 Word/PDF 置为 disabled，并说明剩余条件。
- 任务页只保留一个“使用 AI 协助本任务”主入口，其他 AI 工具放入同一 details 菜单。

- [ ] **Step 4: 增加真实闭环 E2E**

在 `mvp.spec.ts` 保留动态项目 ID，并增加以下顺序：

```ts
test('学生从创建项目进入任务、材料和报告', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  const project = await findProjectWithTasks(page)
  test.skip(!project, '当前演示账号没有可检查任务的项目')
  await page.goto(`/student/projects/${project!.id}/map`)
  await expect(page.locator('.journey-delivery__chapter')).toHaveCount(5)
  await page.locator('.journey-delivery__chapter.is-expanded .journey-delivery__open').first().click()
  await expect(page).toHaveURL(/\/tasks\/\d+$/)
  await expect(page.getByText('使用 AI 协助本任务', { exact: false })).toBeVisible()
  await page.goto(`/student/projects/${project!.id}/materials`)
  await expect(page.getByText('材料档案')).toBeVisible()
  await page.goto(`/student/projects/${project!.id}/report`)
  await expect(page.getByText('报告装配')).toBeVisible()
})
```

- [ ] **Step 5: 验证学生端检查点**

Run:

```bash
cd frontend
npx vitest run src/stores/studentApiModel.test.ts src/journeyDeliveryMapping.test.ts src/journeyTimelineStyles.test.ts
npx playwright test e2e/mvp.spec.ts --grep "学生|研究旅程"
```

Expected: 两条创建路径、五章、任务、材料和报告均使用真实路由与数据。

---

### Task 4: 将学生 AI 工作台拆成 Demo 对应的简单操作层

**Files:**
- Create: `frontend/src/components/ai/AIContextChooser.vue`
- Create: `frontend/src/components/ai/AIResearchWizard.vue`
- Create: `frontend/src/components/ai/AIProjectAssistant.vue`
- Create: `frontend/src/components/ai/AIConversationHistoryDrawer.vue`
- Create: `frontend/src/components/ai/AIToolPicker.vue`
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/stores/aiConversationModel.ts`
- Modify: `frontend/src/aiCenterUI.test.ts`
- Modify: `frontend/src/stores/aiConversationModel.test.ts`
- Modify: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 锁定五个组件的接口**

在 `aiCenterUI.test.ts` 增加源码契约：

```ts
for (const component of [
  'AIContextChooser', 'AIResearchWizard', 'AIProjectAssistant',
  'AIConversationHistoryDrawer', 'AIToolPicker',
]) expect(aiPage).toContain(component)

expect(aiPage.match(/<style scoped>/g)).toHaveLength(1)
expect(aiPage).not.toContain('conversation-sidebar')
```

Expected: RED，因为当前历史仍占据常驻侧栏，页面有三段 scoped style。

- [ ] **Step 2: 创建场景选择组件**

`AIContextChooser.vue` 使用明确 props/emits：

```ts
const props = defineProps<{ mode: 'project' | 'brainstorm' }>()
const emit = defineEmits<{
  select: [mode: 'project' | 'brainstorm']
}>()
```

模板只包含两个入口：

```vue
<section class="ai-context-switch" aria-label="选择 AI 使用场景">
  <button type="button" :aria-pressed="mode === 'project'" @click="emit('select', 'project')">
    <strong>我已有项目课题</strong><small>围绕当前项目、任务和材料继续研究</small>
  </button>
  <button type="button" :aria-pressed="mode === 'brainstorm'" @click="emit('select', 'brainstorm')">
    <strong>我还没有项目课题</strong><small>从真实观察开始，慢慢找到研究问题</small>
  </button>
</section>
```

- [ ] **Step 3: 创建无课题四步向导**

`AIResearchWizard.vue` 接收现有 `ResearchQuestionArtifact`，不直接调用 API：

```ts
const props = defineProps<{
  busy: boolean
  artifact: ResearchQuestionArtifact | null
  error: string
}>()
const emit = defineEmits<{
  generate: [inputs: ResearchQuestionInputs]
  create: [draft: { title: string; problem: string; plan: string; project_type: Project['project_type'] }]
}>()
```

组件内部四步固定为：`发现现象 → 打开问题 → 头脑风暴 → 共同成题`。只有第四步点击“确认并生成项目”才 emit `create`；生成失败不清空内部 draft。

`AICenter.vue` 使用两个适配函数接收子组件数据，再调用已有 API 流程：

```ts
async function handleResearchGenerate(inputs: ResearchQuestionInputs) {
  researchInputs.value = { ...inputs }
  await generateResearchCandidates()
}

async function handleCreateProject(draft: {
  title: string
  problem: string
  plan: string
  project_type: Project['project_type']
}) {
  projectDraft.value = { ...draft }
  await createProjectFromResearch()
}
```

- [ ] **Step 4: 创建已有项目助手**

`AIProjectAssistant.vue` 只显示当前项目和三个目标：

```ts
const props = defineProps<{
  project: Project
  taskId?: number
  busy: boolean
}>()
const emit = defineEmits<{
  prompt: [content: string]
}>()
```

三个目标为“我不知道下一步怎么做”“我想完善研究问题”“我有一个具体问题”。没有项目时不显示通用输入框，只显示返回项目书架的入口。

- [ ] **Step 5: 将历史和工具降为次级抽屉**

- `AIConversationHistoryDrawer.vue` 负责搜索、项目筛选、归档和选择历史。
- `AIToolPicker.vue` 负责关键词、分类和工具选择。
- 两者默认关闭，Escape 关闭，移动端为全宽抽屉。
- AICenter 只负责 API 请求、路由同步、streaming 和把数据传给子组件。

两个抽屉都使用标准 v-model 接口：

```ts
const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{
  'update:modelValue': [value: boolean]
}>()
```

`AICenter.vue` 根结构收敛为：

```vue
<div class="ai-workspace page">
  <PageHeader eyebrow="灵思 AI · 研究伙伴" :title="pageTitle" :description="pageDescription">
    <template #actions>
      <button class="secondary-button" type="button" @click="historyOpen = true">历史对话</button>
      <button v-if="mode === 'project'" class="secondary-button" type="button" @click="toolOpen = true">更多 AI 工具</button>
    </template>
  </PageHeader>
  <AIContextChooser :mode="mode" @select="selectMode" />
  <AIResearchWizard
    v-if="mode === 'brainstorm'"
    :busy="sending || creatingProject"
    :artifact="researchArtifact"
    :error="researchSaveError"
    @generate="handleResearchGenerate"
    @create="handleCreateProject"
  />
  <AIProjectAssistant
    v-else-if="currentProject"
    :project="currentProject"
    :task-id="taskId"
    :busy="sending"
    @prompt="fillQuickPrompt"
  />
  <EmptyState v-else title="先选择一个项目" description="AI 需要绑定正确的项目、任务和材料。" />
  <AIConversationHistoryDrawer
    v-model="historyOpen"
    :conversations="visibleConversations"
    :selected-id="selectedId"
    @select="selectConversation"
  />
  <AIToolPicker
    v-model="toolOpen"
    :agents="agents"
    :selected-key="selectedAgent"
    @select="chooseAgent"
  />
</div>
```

- [ ] **Step 6: 验证 AI 行为不回归**

Run:

```bash
cd frontend
npx vitest run src/aiCenterUI.test.ts src/studentAICenterEntry.test.ts src/stores/aiConversationModel.test.ts
npx playwright test e2e/mvp.spec.ts --grep "AI|无课题"
```

Expected: 无课题确认前不创建项目；已有项目必须绑定项目；真实模型未配置时显示明确阻塞；历史和工具可打开但不占主操作区。

---

### Task 5: 将教师端迁移为“待办—项目—审核”的真实工作台

**Files:**
- Create: `frontend/src/components/teacher/TeacherHomePanel.vue`
- Create: `frontend/src/components/teacher/TeacherProjectPool.vue`
- Create: `frontend/src/components/teacher/TeacherProjectRows.vue`
- Create: `frontend/src/components/teacher/TeacherReviewInbox.vue`
- Create: `frontend/src/components/teacher/TeacherReviewDetail.vue`
- Modify: `frontend/src/pages/teacher/TeacherWorkbench.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectDetail.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectTemplate.vue`
- Modify: `frontend/src/components/TeacherAIPreReview.vue`
- Modify: `frontend/src/teacherAIReviewUI.test.ts`
- Modify: `frontend/src/stores/teacherProjectModel.test.ts`
- Modify: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 锁定工作台拆分和审核边界**

在 `teacherAIReviewUI.test.ts` 增加：

```ts
expect(workbench).toContain('TeacherReviewDetail')
expect(preReview).toContain("defineEmits")
expect(preReview).toContain("adopt")
expect(preReview).not.toContain('reviewMaterialRevision')
expect(preReview).not.toContain('通过并解锁')
```

Expected: RED，因为当前 `TeacherWorkbench.vue` 仍同时承载多个 surface，AI 结果还不能写入评语草稿。

- [ ] **Step 2: 按路由 surface 拆分教师页面**

`TeacherWorkbench.vue` 保留数据加载和路由分发：

```vue
<TeacherHomePanel v-if="surface === 'home'" :summary="summary" :items="inbox" />
<TeacherProjectPool v-else-if="surface === 'pool'" :projects="poolProjects" @claim="claimProject" />
<TeacherProjectRows v-else-if="surface === 'projects'" :projects="projects" />
<TeacherReviewInbox v-else-if="surface === 'reviews'" :items="reviewItems" />
<TeacherReviewDetail v-else :revision="selectedRevision" @review="submitReview" />
```

每个子组件只渲染一个页面职责，不自行请求 API。

- [ ] **Step 3: 将 AI 预审建议写入评语草稿**

`TeacherAIPreReview.vue` 增加 advisory emit：

```ts
const emit = defineEmits<{
  adopt: [comment: string]
}>()

function adoptSuggestion() {
  const comment = generation.value?.output_text?.trim()
  if (comment) emit('adopt', comment)
}
```

模板按钮必须写明“写入评语草稿”，不出现审核状态操作：

```vue
<button class="secondary-button" type="button" :disabled="!generation?.output_text" @click="adoptSuggestion">
  写入评语草稿
</button>
```

`TeacherReviewDetail.vue` 接收后只更新本地 `comment`，教师仍需点击现有“通过审核”或“退回修改”。

- [ ] **Step 4: 保留五章项目详情和唯一范本入口**

- `TeacherProjectDetail.vue` 只显示项目摘要、五章节和右侧指导动作。
- 每个材料只有一个审核入口。
- “配置材料范本”只出现在详情页，继续使用 `/teacher/projects/:id/template`。
- `TeacherProjectTemplate.vue` 直接访问时自行加载项目和模板，不依赖先访问详情页。

- [ ] **Step 5: 验证教师端**

Run:

```bash
cd frontend
npx vitest run src/teacherAIReviewUI.test.ts src/stores/teacherProjectModel.test.ts src/teacherPoolStyles.test.ts
npx playwright test e2e/mvp.spec.ts --grep "教师|审核"
```

Expected: 项目列表不重复问题和方案；AI 只写入评语草稿；教师最终操作保持原权限和 API。

---

### Task 6: 对齐平台端和公共内容页面

**Files:**
- Modify: `frontend/src/pages/platform/PlatformConsole.vue`
- Modify: `frontend/src/pages/platform/SchoolDetail.vue`
- Modify: `frontend/src/pages/platform/PlatformAIAgents.vue`
- Modify: `frontend/src/pages/platform/PlatformCases.vue`
- Modify: `frontend/src/pages/platform/PlatformSettings.vue`
- Modify: `frontend/src/pages/shared/ContentLibrary.vue`
- Modify: `frontend/src/pages/teacher/TeacherAnnouncements.vue`
- Modify: `frontend/src/stores/navigationRegistry.ts`
- Modify: `frontend/src/stores/navigationRegistry.test.ts`
- Modify: `frontend/e2e/mvp.spec.ts`

- [ ] **Step 1: 统一内容筛选模型**

在 `ContentLibrary.vue`、`PlatformAIAgents.vue` 和 `PlatformConsole.vue` 使用同一个前端筛选输入结构：

```ts
interface WorkspaceFilters {
  keyword: string
  category: string
  status: string
}
```

每个页面的 computed 只筛选已加载数据，不新增 API 查询协议。

- [ ] **Step 2: 保留平台页面单一职责**

- `PlatformConsole.vue` 只处理 `home`、`schools`、`competitions`、`announcements`。
- `SchoolDetail.vue` 负责学校信息、授权和审计记录。
- `PlatformAIAgents.vue` 负责模板名称、角色、分组、状态和编辑。
- `PlatformCases.vue` 负责公开案例治理。
- `PlatformSettings.vue` 只显示安全策略和服务健康。

- [ ] **Step 3: 统一桌面表格和移动卡片**

学校和 AI 模板在宽屏使用表格，在 768px 以下使用同一数据源的卡片：

```vue
<div class="workspace-table desktop-only">
  <el-table :data="sortedAgents">
    <el-table-column prop="name" label="模板名称" min-width="180" />
    <el-table-column prop="category" label="分组" width="130" />
    <el-table-column label="状态" width="110">
      <template #default="{ row }"><StatusTag :status="row.is_active ? 'active' : 'disabled'" /></template>
    </el-table-column>
  </el-table>
</div>
<div class="workspace-card-list mobile-only">
  <article v-for="agent in sortedAgents" :key="agent.id" class="paper-card workspace-data-card">
    <div><strong>{{ agent.name }}</strong><small>{{ roleLabels[agent.role] }} · {{ agent.category }}</small></div>
    <StatusTag :status="agent.is_active ? 'active' : 'disabled'" />
    <button class="secondary-button" type="button" @click="openEdit(agent)">编辑</button>
  </article>
</div>
```

学校名称或“查看详情”负责导航，授权 switch 只负责启停；禁止整行链接包裹 switch。

- [ ] **Step 4: 验证平台端**

Run:

```bash
cd frontend
npx vitest run src/stores/navigationRegistry.test.ts src/platformLicenseStyles.test.ts
npx playwright test e2e/mvp.spec.ts --grep "平台|学校|AI 助手模板"
```

Expected: 平台导航只有唯一入口，表格与开关无嵌套交互，移动端无文档级横向溢出。

---

### Task 7: 删除旧实现并拆分全局样式

**Files:**
- Delete: `frontend/src/components/JourneyStageDetail.vue`
- Delete: `frontend/src/components/ProjectTimeline.vue`
- Delete: `frontend/src/components/MaterialAIAssistant.vue`
- Delete: `frontend/src/components/JourneyStepList.vue`
- Delete: `frontend/src/components/ConsistencyCheckCard.vue`
- Delete: `frontend/src/components/JourneyDeliverableCard.vue`
- Delete: `frontend/src/components/JourneyDeliveryManifest.vue`
- Create: `frontend/src/styles/tokens.css`
- Create: `frontend/src/styles/foundations.css`
- Create: `frontend/src/styles/workspace.css`
- Create: `frontend/src/styles/element-plus.css`
- Create: `frontend/src/styles/responsive.css`
- Modify: `frontend/src/lingsu-system.css`
- Modify: `frontend/src/designSystemStyles.test.ts`
- Modify: `frontend/src/studentAICenterEntry.test.ts`

- [ ] **Step 1: 再次证明旧组件无生产引用**

Run:

```bash
cd ..
rg -n "JourneyStageDetail|ProjectTimeline|MaterialAIAssistant|JourneyStepList|ConsistencyCheckCard|JourneyDeliverableCard|JourneyDeliveryManifest" frontend/src --glob '!components/*.vue' --glob '!*.test.ts'
```

Expected: 无输出。若出现真实 import，先迁移调用方，不能删除仍在使用的组件。

- [ ] **Step 2: 删除确认无引用的组件**

通过 `apply_patch` 删除上面七个文件；同步删除仅用于断言“未引用”的旧测试字符串，不改业务测试。

- [ ] **Step 3: 按职责拆分 CSS**

`lingsu-system.css` 最终只保留导入顺序：

```css
@import './styles/tokens.css';
@import './styles/foundations.css';
@import './styles/workspace.css';
@import './styles/element-plus.css';
@import './styles/responsive.css';
```

迁移规则固定如下：

- `tokens.css`：字体 import、`:root` 和 Element Plus 变量。
- `foundations.css`：reset、body、字体、链接、焦点、按钮、表单、状态标签。
- `workspace.css`：三端 portal/layout、PageHeader、卡片、列表、表格、章节、AI、审核和内容页面组件。
- `element-plus.css`：所有 `.el-` 开头覆盖。
- `responsive.css`：所有 `@media` 和 `prefers-reduced-motion`。

迁移只改变文件位置，不同时重命名选择器或改变数值；视觉调整必须在前六个任务完成。

- [ ] **Step 4: 更新设计系统测试读取拆分文件**

```ts
const styles = [
  './styles/tokens.css', './styles/foundations.css', './styles/workspace.css',
  './styles/element-plus.css', './styles/responsive.css',
].map((path) => readFileSync(new URL(path, import.meta.url), 'utf8')).join('\n')
```

- [ ] **Step 5: 验证没有旧层叠残留**

Run:

```bash
cd frontend
npx vitest run src/designSystemStyles.test.ts src/studentAICenterEntry.test.ts
npm run build
```

Expected: 构建通过；AICenter 只有一个 scoped style；全局入口 CSS 导入顺序稳定。

---

### Task 8: 全路由视觉、交互和业务回归

**Files:**
- Modify: `frontend/e2e/mvp.spec.ts`
- Modify: `docs/MVP验收清单.md`
- Modify: `docs/项目运行说明.md`

- [ ] **Step 1: 增加全部真实路由的溢出检查**

E2E 使用角色登录和动态项目 ID，遍历 390、768、1024、1280、1440px：

```ts
const viewports = [390, 768, 1024, 1280, 1440]

for (const width of viewports) {
  await page.setViewportSize({ width, height: 900 })
  await expect.poll(() => page.evaluate(() =>
    document.documentElement.scrollWidth <= window.innerWidth
  )).toBeTruthy()
}
```

项目详情、任务、材料、报告和教师项目详情必须通过 API 动态获取 ID，不使用 `1`、`6`、`8` 等固定值。

- [ ] **Step 2: 检查关键交互**

E2E 必须覆盖：

- 未登录入口、登录、注册表单校验。
- 已有课题创建项目。
- 无课题 AI 四步引导；未配置模型时显示阻塞。
- 五章展开、任务进入、材料查看、报告导出锁定条件。
- 教师认领、项目详情、AI 预审写入评语草稿、教师通过/退回。
- 学校详情链接与授权开关互不干扰。
- AI 模板筛选和移动卡片。
- Escape 关闭菜单/抽屉，Tab/aria-selected 状态正确。

- [ ] **Step 3: 运行最终验证**

Run:

```bash
cd frontend
npm run test
npm run build
npm run test:e2e
cd ../backend
python manage.py test apps.core.tests
cd ..
git diff --check
```

Expected:

- Vitest 全部通过。
- Vite/Vue TypeScript 构建通过。
- Playwright 全部通过且五种视口无文档级横向溢出。
- Django 核心测试全部通过。
- `git diff --check` 无输出。

- [ ] **Step 4: 浏览器逐页视觉检查**

至少人工检查以下页面：

- 公共：入口、登录、注册。
- 学生：首页、项目书架、创建项目、五章旅程、任务、材料、报告、AI 两种场景。
- 教师：工作台、项目池、指导项目、项目详情、审核、AI 预审、材料范本。
- 平台：概览、学校列表、学校详情、AI 模板、运营内容、设置。

记录每页检查过的视口、控制台错误和遗留风险；不把“未检查”写成“通过”。

---

## 完成条件

- Demo 中每个页面都有明确的真实生产路由或明确的上下文内入口。
- 学生端有课题和无课题两条路径都能创建真实项目，确认前不产生空项目。
- AI 工作台主界面不再被历史、工具列表和技术术语占据。
- 学生任务、材料、报告形成完整闭环。
- 教师 AI 预审能生成并写入评语草稿，但不能自动审核。
- 五章节是学生、教师、材料和报告页面唯一进度模型。
- 平台端学校、模板和内容操作没有嵌套点击或重复入口。
- 已失效的旅程和 AI 旧组件已删除，不再保留两套实现。
- 全量测试、构建、E2E、Django 测试和浏览器检查完成。

## 执行顺序

按 Task 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 顺序执行。每完成一个 Task 都先运行其 focused tests；Task 7 只能在前六项生产迁移完成并确认旧组件无引用后执行。
