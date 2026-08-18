# 灵溯三端门户 UI 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将灵溯前端改造成以“暖白研究手帐”为统一视觉系统、但学生/教师/平台三端职责完全分离的可交互门户。

**Architecture:** 路由仍以 `/student`、`/teacher`、`/platform` 为入口，但每一端改为独立页面组件，不再由一个条件分支仪表板承载。页面使用本轮 UI 演示数据和纯前端交互状态，保留后续 API 适配边界；学生端的任务抽屉、教师审核反馈、平台授权状态均有独立的可测试状态模块。

**Tech Stack:** Vue 3、TypeScript、Vue Router、Element Plus 图标、Vitest、Vite。

---

### Task 1: 建立三端可验证的 UI 状态模型

**Files:**
- Create: `frontend/src/stores/portalUi.ts`
- Test: `frontend/src/stores/portalUi.test.ts`

- [ ] **Step 1: 写入失败测试**

```ts
import { describe, expect, it } from 'vitest'
import { nextStudentTask, reviewSubmission, schoolStatus } from './portalUi'

describe('portal UI state', () => {
  it('puts a returned student task ahead of normal work', () => {
    expect(nextStudentTask([{ id: 'a', status: 'open' }, { id: 'b', status: 'repair' }])?.id).toBe('b')
  })
  it('records concrete teacher feedback when work is returned', () => {
    expect(reviewSubmission('submitted', 'return', '补充测量方法')).toEqual({ status: 'repair', feedback: '补充测量方法' })
  })
  it('shows an expired school as read only', () => {
    expect(schoolStatus({ active: true, expiresOn: '2026-08-01' }, '2026-08-12')).toBe('expired')
  })
})
```

- [ ] **Step 2: 验证测试为红色**

Run: `cd frontend && npm test -- src/stores/portalUi.test.ts`

Expected: FAIL because `portalUi` does not exist.

- [ ] **Step 3: 实现最小状态函数**

```ts
export type UiTask = { id: string; status: 'open' | 'submitted' | 'repair' | 'done' }
export const nextStudentTask = (tasks: UiTask[]) => tasks.find((task) => task.status === 'repair') ?? tasks.find((task) => task.status === 'open')
export const reviewSubmission = (_status: string, outcome: 'approve' | 'return', feedback = '') => outcome === 'approve' ? { status: 'done' as const, feedback: '' } : { status: 'repair' as const, feedback }
export const schoolStatus = (school: { active: boolean; expiresOn: string }, today: string) => !school.active ? 'disabled' : school.expiresOn < today ? 'expired' : 'active'
```

- [ ] **Step 4: 验证测试为绿色**

Run: `cd frontend && npm test -- src/stores/portalUi.test.ts`

Expected: PASS.

### Task 2: 提取暖白研究手帐的共享框架和视觉令牌

**Files:**
- Create: `frontend/src/components/PortalTopbar.vue`
- Create: `frontend/src/components/BotanicalMark.vue`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/main.ts`

- [ ] **Step 1: 定义视觉令牌和布局约束**

```css
:root { --paper:#fbfaf6; --canvas:#f7f5ef; --ink:#2b312c; --moss:#53765b; --repair:#b96a4e; --rule:#e7e1d5; }
.lingsu-page { min-height:100vh; background:var(--canvas); color:var(--ink); }
.paper-sheet { background:var(--paper); border:1px solid var(--rule); box-shadow:0 10px 22px rgba(68,55,34,.06); }
```

- [ ] **Step 2: 建立顶部品牌栏**

```vue
<PortalTopbar role-label="学生端" user-name="林同学" />
```

- [ ] **Step 3: 为小屏幕提供单列适配**

```css
@media (max-width: 900px) { .portal-grid { grid-template-columns:1fr; } .desktop-only { display:none; } }
```

- [ ] **Step 4: 运行类型检查与构建**

Run: `cd frontend && npm run build`

Expected: PASS.

### Task 3: 构建独立学生任务旅程页面

**Files:**
- Create: `frontend/src/pages/StudentPortal.vue`
- Modify: `frontend/src/router.ts`
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/stores/portalUi.test.ts`

- [ ] **Step 1: 增加学生任务优先级断言**

```ts
it('uses the first open task when no repair task exists', () => {
  expect(nextStudentTask([{ id: 'first', status: 'open' }, { id: 'later', status: 'open' }])?.id).toBe('first')
})
```

- [ ] **Step 2: 验证新增断言绿色**

Run: `cd frontend && npm test -- src/stores/portalUi.test.ts`

Expected: PASS.

- [ ] **Step 3: 以参考图的比例实现任务旅程**

```vue
<section class="student-layout">
  <nav class="research-trail" aria-label="研究旅程">...</nav>
  <main class="paper-sheet task-sheet">...</main>
  <aside class="ai-coach">...</aside>
</section>
```

- [ ] **Step 4: 接入真实的 UI 交互**

```ts
const taskText = ref('')
const aiPromptOpen = ref(false)
const submitted = ref(false)
```

- [ ] **Step 5: 手动验证**

Open: `http://127.0.0.1:5173/student`

Expected: 输入、AI 提示展开、材料提交成功状态均可见；路由地址保持 `/student`。

### Task 4: 构建独立教师审核和平台授权页面

**Files:**
- Create: `frontend/src/pages/TeacherPortal.vue`
- Create: `frontend/src/pages/PlatformPortal.vue`
- Modify: `frontend/src/router.ts`
- Modify: `frontend/src/App.vue`
- Test: `frontend/src/stores/portalUi.test.ts`

- [ ] **Step 1: 写入审核与授权状态失败测试**

```ts
it('marks approved submission complete', () => {
  expect(reviewSubmission('submitted', 'approve')).toEqual({ status: 'done', feedback: '' })
})
it('makes disabled school take precedence over expiry', () => {
  expect(schoolStatus({ active: false, expiresOn: '2027-01-01' }, '2026-08-12')).toBe('disabled')
})
```

- [ ] **Step 2: 验证与实现**

Run: `cd frontend && npm test -- src/stores/portalUi.test.ts`

Expected: PASS after using the Task 1 state functions.

- [ ] **Step 3: 实现教师审核桌**

```vue
<section class="teacher-layout"><aside class="review-queue">...</aside><main class="paper-sheet review-document">...</main><aside class="review-decision">...</aside></section>
```

- [ ] **Step 4: 实现平台授权桌**

```vue
<section class="platform-layout"><nav class="platform-nav">...</nav><main><table class="school-table">...</table></main></section>
```

- [ ] **Step 5: 验证路由隔离**

Run: `cd frontend && npm test && npm run build`

Expected: PASS; `/student`、`/teacher`、`/platform` 分别加载独立页面组件。

### Task 5: 浏览器设计 QA

**Files:**
- Create: `design-qa.md`

- [ ] **Step 1: 启动本地 Vite 页面并抓取三端**

Run: `cd frontend && npm run dev -- --host 127.0.0.1`

Expected: `/student`、`/teacher`、`/platform` 均可访问。

- [ ] **Step 2: 将学生端与已选参考图并排比较**

Source: `/Users/anzhi/.codex/generated_images/019ff4e9-d008-7f62-9c01-108ff98b8786/exec-f15755d7-f152-43cd-8ae4-197ce0676bf0.png`

- [ ] **Step 3: 修复所有 P0/P1/P2 差异并记录**

```md
final result: passed
```

- [ ] **Step 4: 运行全量验证**

Run: `cd frontend && npm test && npm run build`

Expected: PASS.
