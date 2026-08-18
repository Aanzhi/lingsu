# 灵溯学生任务地图 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把学生项目页升级为由真实材料审核状态驱动的分阶段任务地图。

**Architecture:** 新增前端纯函数模块，将 Material 和 MaterialRevision 派生为阶段、解锁、任务状态、下一任务与勋章；`App.vue` 只渲染数据并复用既有材料 API，不新增后端模型。

**Tech Stack:** Vue 3、TypeScript、Vitest、Element Plus、Django REST API。

---

### Task 1: 建立任务地图领域模型

**Files:**
- Create: `frontend/src/stores/taskMap.ts`
- Create: `frontend/src/stores/taskMap.test.ts`

- [ ] **Step 1: 写失败测试**

```ts
import { describe, expect, it } from 'vitest'
import { buildTaskMap } from './taskMap'
const material = (title: string, status: string) => ({ title, status, revisions: [] })
describe('student task map', () => {
  it('locks later stages before their gate is approved', () => {
    expect(buildTaskMap([]).stages[1].locked).toBe(true)
    expect(buildTaskMap([material('开题报告', 'approved')]).stages[1].locked).toBe(false)
  })
  it('prioritizes returned work', () => {
    expect(buildTaskMap([material('开题报告', 'approved'), material('问卷调查', 'revision_required')]).nextTask?.status).toBe('repair')
  })
  it('lights a badge only for approved gate evidence', () => {
    expect(buildTaskMap([material('开题报告', 'approved')]).badges.find(b => b.id === 'problem-finder')?.unlocked).toBe(true)
  })
})
```

- [ ] **Step 2: 确认测试为红**

Run: `cd frontend && npm test -- --run src/stores/taskMap.test.ts`

Expected: FAIL，模块不存在。

- [ ] **Step 3: 实现最小模型与固定任务**

```ts
export type TaskStatus = 'locked' | 'not_started' | 'in_progress' | 'submitted' | 'repair' | 'completed'
export type MaterialSnapshot = { title: string; status: string; revisions?: Array<{ status: string; review_comment?: string }> }
export const buildTaskMap = (materials: MaterialSnapshot[]) => ({ stages: [], badges: [], nextTask: null, completedTaskCount: 0, overallProgress: 0 })
```

Replace the placeholder with five stages: 开题（项目开题、项目设计草图、开题报告）, 方案设计（问卷调查、程序流程图、硬件接线图）, 调研与制作（项目日志、过程照片、实物制作、源代码）, 成果申报（项目报告、申报材料、查重报告、项目介绍 PPT/视频）, 答辩挑战（答辩模拟演练、评委问答）。 Map no material/draft/submitted/revision_required/approved to 未开始/进行中/待审核/需修复/已完成. Gates are 开题报告；任一方案材料；项目日志加任一过程证据；项目报告. Repair has priority over unfinished task in unlocked stages.

- [ ] **Step 4: 确认测试为绿并提交**

Run: `cd frontend && npm test -- --run src/stores/taskMap.test.ts`

Expected: 3 tests PASS.

```bash
git add frontend/src/stores/taskMap.ts frontend/src/stores/taskMap.test.ts
git commit -m "feat: derive student task map from materials"
```

### Task 2: 映射教师打回意见与勋章进度

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/stores/taskMap.ts`
- Test: `frontend/src/stores/taskMap.test.ts`

- [ ] **Step 1: 添加失败测试**

```ts
it('exposes feedback for a returned task', () => {
  const map = buildTaskMap([{ title: '开题报告', status: 'revision_required', revisions: [{ status: 'revision_required', review_comment: '补充可测量的指标。' }] }])
  expect(map.stages[0].tasks[2].feedback).toContain('可测量')
})
it('reports five achievement slots and completed count', () => {
  const map = buildTaskMap([material('开题报告', 'approved')])
  expect(map.badges).toHaveLength(5)
  expect(map.completedTaskCount).toBeGreaterThan(0)
})
```

- [ ] **Step 2: 确认失败后实现映射**

Run: `cd frontend && npm test -- --run src/stores/taskMap.test.ts`

Add `review_comment?: string` to `MaterialRevision`. Map the latest non-empty comment to `task.feedback`. Return `completedTaskCount`, `overallProgress` and five immutable badges: 问题发现者、方案设计师、实验探索者、成果创造者、答辩挑战者. Badge unlocking is derived only from approved gate evidence.

- [ ] **Step 3: 确认通过并提交**

Run: `cd frontend && npm test -- --run src/stores/taskMap.test.ts`

Expected: 5 tests PASS.

```bash
git add frontend/src/api.ts frontend/src/stores/taskMap.ts frontend/src/stores/taskMap.test.ts
git commit -m "feat: show task feedback and achievements"
```

### Task 3: 实现项目任务地图页面

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`

- [ ] **Step 1: 在组件声明派生状态**

```ts
const selectedStageId = ref('kickoff')
const taskMap = computed(() => buildTaskMap(materials.value))
const selectedStage = computed(() => taskMap.value.stages.find(stage => stage.id === selectedStageId.value) ?? taskMap.value.stages[0])
```

- [ ] **Step 2: 替换学生项目路由内容**

For a student project, render current next task plus nearest competition deadline, a five-stage vertical route, `已获 X / 5` badges, and the selected unlocked stage as a horizontal task rail. Keep empty/pending proposal states unchanged. Clicking a locked stage must use `ElMessage.info(stage.unlockHint)` and never open an editor.

- [ ] **Step 3: 添加响应式极简北欧风样式**

```css
.task-map-rail { display:grid; grid-auto-flow:column; grid-auto-columns:minmax(220px,1fr); overflow-x:auto; }
@media (max-width:720px) { .task-map-rail { grid-auto-flow:row; grid-template-columns:1fr; } }
```

Use existing pale backgrounds, forest-green active accents, muted locked cards, card whitespace and no points/rankings/leaderboard/shop.

- [ ] **Step 4: 测试、构建并提交**

Run: `cd frontend && npm test && npm run build`

Expected: all tests pass and Vite build succeeds.

```bash
git add frontend/src/App.vue frontend/src/style.css frontend/src/stores/taskMap.ts frontend/src/stores/taskMap.test.ts
git commit -m "feat: add student project task map"
```

### Task 4: 从任务卡编辑真实材料

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/stores/dashboard.ts`
- Modify: `frontend/src/stores/studentFlow.ts`
- Test: `frontend/src/stores/studentFlow.test.ts`

- [ ] **Step 1: 写编辑许可的失败测试**

```ts
import { taskEditorMode } from './studentFlow'
it('does not allow a locked task to open an editor', () => {
  expect(taskEditorMode('not_started')).toBe('edit')
  expect(taskEditorMode('repair')).toBe('edit')
  expect(taskEditorMode('locked')).toBe('locked')
})
```

- [ ] **Step 2: 确认失败后实现守卫**

Run: `cd frontend && npm test -- --run src/stores/studentFlow.test.ts`

```ts
export const taskEditorMode = (status: string) => status === 'locked' ? 'locked' : 'edit'
```

- [ ] **Step 3: 连接任务抽屉**

Extend `DrawerKind` with `task`. `openTask(task)` rejects locks, reuses its `materialTitle` material or creates it with `createMaterial`, loads its latest content, and opens an editor. Reuse revision creation and truth-confirmed submission, replacing the material in `materials` to refresh map state instantly. The drawer displays repair feedback, makes an AI preview from `task.aiGoal`, adopts via `adoptAiPreview` only after click, and requires truth confirmation before submit.

- [ ] **Step 4: 完整验证并提交**

Run: `cd frontend && npm test && npm run build`

Expected: all tests pass and build succeeds.

```bash
git add frontend/src/App.vue frontend/src/stores/dashboard.ts frontend/src/stores/studentFlow.ts frontend/src/stores/studentFlow.test.ts
git commit -m "feat: edit project materials from task map"
```

### Task 5: 服务与路由验收

**Files:**
- Modify: `README.md` only if startup instructions change

- [ ] **Step 1: 运行全套校验**

Run: `cd frontend && npm test && npm run build && cd ../backend && /opt/anaconda3/bin/python3.12 manage.py test && /opt/anaconda3/bin/python3.12 manage.py check`

Expected: frontend test/build and Django test/check all pass.

- [ ] **Step 2: 验证直接路由与交互**

Run: `curl -I http://127.0.0.1:5173/projects && curl -s http://127.0.0.1:8000/api/me/`

Expected: Vite returns `200 OK`, API returns demo-session JSON. In browser refresh `/projects`, open a material task and verify it becomes 待审核 without a full page reload.

## Self-review

- Tasks 1–2 implement all fixed mappings, gates, status, feedback and approved-evidence badges.
- Task 3 implements route, horizontal map, stage route, deadline, achievement summary and mobile fallback.
- Task 4 implements locks, materials, AI preview and authenticity confirmation.
- Task 5 covers frontend, backend, browser route and API regression validation.

