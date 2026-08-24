# 灵溯全站功能与 UI 重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不破坏现有业务数据和控制台独立性的前提下，先完成覆盖全站的方案 B UI 与真实交互，再补齐项目生命周期、研究旅程、AI、审核、成果展示和通知的实际业务闭环。

**Architecture:** 采用“领域契约 → fixture UI → 真实 API → 全量验收”的顺序。学生端使用独立的全屏顶部导航壳，教师端和平台端复用方案 B 管理壳，公共入口全屏，项目控制台继续作为宿主机独立进程。现有 Django/DRF 模型、Vue/Pinia 状态和私有文件上传能力优先复用，只为当前项目、AI 分类、实验日志强校验、成果同意链和 30 天清理补齐最小接口。

**Tech Stack:** Vue 3、TypeScript、Vite、Element Plus、Pinia、Vue Router、Vitest、Playwright、Django 5.1、Django REST Framework、PostgreSQL、Celery、Redis、标准库 Python 控制台。

---

## 执行前约束

- 从当前工作树继续，禁止 `git reset --hard`、`git checkout --` 或覆盖用户已有修改。
- 每个任务先写失败测试，再实现最小行为，再运行该任务的定向测试；任务完成后只提交该任务涉及的文件。
- 前端 UI 阶段只能使用确定性 fixture/ViewModel，不执行真实业务写入；API 接入阶段才启用真实写操作。
- 方案 B 是唯一视觉基准：系统无衬线字体、统一壳层、组件令牌、PC 1280/1440 验收；不建设移动端布局。
- 控制台不加入 `docker-compose.yml`，不从业务登录鉴权，不因 Docker/项目停止而退出。

## Task 1: 建立前端领域契约与全站路由基线

**Files:**
- Create: `frontend/src/stores/productContracts.ts`
- Create: `frontend/src/stores/productContracts.test.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/router.ts`
- Test: `frontend/src/router.test.ts`

- [ ] **Step 1: Write the failing contract tests**

在 `frontend/src/stores/productContracts.test.ts` 固定以下业务值，防止页面重新使用互不兼容的字符串：

```ts
import { describe, expect, it } from 'vitest'
import {
  AI_WORKSPACE_MODES,
  PROJECT_LIFECYCLE_STATES,
  JOURNEY_TASK_STATES,
} from './productContracts'

describe('product contracts', () => {
  it('exposes the three approved AI workspace modes', () => {
    expect(AI_WORKSPACE_MODES).toEqual([
      { key: 'opening', label: '开题' },
      { key: 'research', label: '研究' },
      { key: 'defense', label: '答辩' },
    ])
  })

  it('keeps project and journey states explicit', () => {
    expect(PROJECT_LIFECYCLE_STATES).toEqual(['unclaimed', 'active', 'completed', 'archived', 'trashed'])
    expect(JOURNEY_TASK_STATES).toEqual(['available', 'in_progress', 'pending_review', 'revision_required', 'approved', 'completed'])
  })

})
```

在 `frontend/src/router.test.ts` 增加路由断言：公共入口、普通登录、平台登录、学生通知、教师通知和现有详情路由均存在；学生端仍以 `/student/home` 为默认入口。

- [ ] **Step 2: Run the tests and verify they fail**

Run: `npm --prefix frontend test -- --run src/stores/productContracts.test.ts src/router.test.ts`

Expected: FAIL because `productContracts.ts` and the notification routes do not yet exist.

- [ ] **Step 3: Implement the shared contract**

在 `frontend/src/stores/productContracts.ts` 定义并导出：

```ts
export const AI_WORKSPACE_MODES = [
  { key: 'opening', label: '开题' },
  { key: 'research', label: '研究' },
  { key: 'defense', label: '答辩' },
] as const

export type AIWorkspaceMode = typeof AI_WORKSPACE_MODES[number]['key']
export const PROJECT_LIFECYCLE_STATES = ['unclaimed', 'active', 'completed', 'archived', 'trashed'] as const
export const JOURNEY_TASK_STATES = ['available', 'in_progress', 'pending_review', 'revision_required', 'approved', 'completed'] as const
export type ProjectLifecycleState = typeof PROJECT_LIFECYCLE_STATES[number]
export type JourneyTaskState = typeof JOURNEY_TASK_STATES[number]

export interface CurrentProjectContext {
  id: number | null
  title: string | null
  status: ProjectLifecycleState | null
  materialCount: number
  unreadReviewCount: number
}
```

在 `api.ts` 为 `Project`、`Material`、`ProjectTask`、`AIConversation` 和 `PublicCase` 增加与契约一致的前端类型；保留现有接口函数名称，新增 `setPrimaryProject`、通知读取和后续显式 AI 保存接口的类型声明。为 `/student/notifications` 和 `/teacher/notifications` 增加路由，组件在后续任务实现。

- [ ] **Step 4: Run the contract and route tests**

Run: `npm --prefix frontend test -- --run src/stores/productContracts.test.ts src/router.test.ts`

Expected: PASS。

- [ ] **Step 5: Commit the contract boundary**

```bash
git add frontend/src/stores/productContracts.ts frontend/src/stores/productContracts.test.ts frontend/src/api.ts frontend/src/router.ts frontend/src/router.test.ts
git commit -m "feat: define lingsu frontend product contracts"
```

## Task 2: 统一公共、学生、教师和平台壳层

**Files:**
- Create: `frontend/src/components/PublicShell.vue`
- Create: `frontend/src/components/StudentPortalShell.vue`
- Modify: `frontend/src/components/WorkspaceShell.vue`
- Modify: `frontend/src/components/WorkspaceFrame.vue`
- Modify: `frontend/src/components/AppTopbar.vue`
- Modify: `frontend/src/layouts/StudentLayout.vue`
- Modify: `frontend/src/layouts/TeacherLayout.vue`
- Modify: `frontend/src/layouts/PlatformLayout.vue`
- Modify: `frontend/src/stores/navigationRegistry.ts`
- Modify: `frontend/src/styles/tokens.css`
- Modify: `frontend/src/styles/workspace.css`
- Modify: `frontend/src/lingsu-system.css`
- Test: `frontend/src/studentNavigationLayout.test.ts`
- Test: `frontend/src/fullSiteVisualConsistency.test.ts`

- [ ] **Step 1: Add failing shell assertions**

在 `studentNavigationLayout.test.ts` 固定学生端不渲染 `workspace-sidebar`、渲染顶部导航并显示“首页 / 我的项目 / 灵思 AI / 研究旅程 / 材料档案 / 项目邀请 / 成果申请”；在 `fullSiteVisualConsistency.test.ts` 固定公共入口无侧栏和底部提示，教师/平台仍拥有 232px 管理侧栏。

```ts
expect(studentHtml).not.toContain('workspace-sidebar')
expect(studentHtml).toContain('student-top-navigation')
expect(publicHtml).not.toContain('workspace-sidebar')
expect(publicHtml).not.toContain('sidebar-note')
expect(teacherCss).toContain('grid-template-columns:232px')
```

- [ ] **Step 2: Run the shell tests and verify the current layout fails**

Run: `npm --prefix frontend test -- --run src/studentNavigationLayout.test.ts src/fullSiteVisualConsistency.test.ts`

Expected: FAIL because `StudentLayout.vue` currently delegates to the sidebar `WorkspaceShell`.

- [ ] **Step 3: Implement the shell split**

`PublicShell.vue` 只提供全屏顶栏和 `RouterView` 内容容器；不渲染侧栏、角色 chip、Demo tips 或底部提示。

`StudentPortalShell.vue` 提供统一顶栏、当前项目选择器、顶部路由导航、通知入口和用户菜单；内容区占满剩余 PC 视口，首页 Hero 不受侧栏挤压。

`WorkspaceShell.vue` 保留教师/平台管理壳，只接受 `role`、`roleTone`、`sectionLabel` 和导航数据；删除任何“公共入口 / 学生端 / 教师端 / 平台端 / 项目控制台”角色切换文案。

`navigationRegistry.ts` 调整学生导航为顶部导航所需的扁平结构；教师和平台保留侧栏结构。所有角色只显示当前端名称，不显示跨端入口。

`tokens.css` 和 `workspace.css` 固定方案 B 的系统字体、66px 顶栏、232px 管理侧栏、12px 卡片圆角、统一边框/阴影/间距和管理端青灰强调色；公共/学生使用苔绿色。

- [ ] **Step 4: Verify at both PC widths**

Run: `npm --prefix frontend run build`。

Then run the visual test suite with the browser matrix in Task 11; at 1280px and 1440px assert `document.documentElement.scrollWidth <= window.innerWidth` for every route.

- [ ] **Step 5: Commit shared shells**

```bash
git add frontend/src/components frontend/src/layouts frontend/src/stores/navigationRegistry.ts frontend/src/styles frontend/src/lingsu-system.css frontend/src/studentNavigationLayout.test.ts frontend/src/fullSiteVisualConsistency.test.ts
git commit -m "feat: unify lingsu workspace shells"
```

## Task 3: 完成公共端和学生端 fixture-first 页面

**Files:**
- Create: `frontend/src/fixtures/portalFixtures.ts`
- Create: `frontend/src/stores/studentPortalModel.ts`
- Create: `frontend/src/stores/studentPortalModel.test.ts`
- Create: `frontend/src/pages/student/StudentNotifications.vue`
- Modify: `frontend/src/pages/public/EntryPage.vue`
- Modify: `frontend/src/pages/public/LoginPage.vue`
- Modify: `frontend/src/pages/public/RegisterPage.vue`
- Modify: `frontend/src/pages/public/PlatformLoginPage.vue`
- Modify: `frontend/src/pages/student/StudentHome.vue`
- Modify: `frontend/src/pages/student/StudentProjects.vue`
- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/pages/student/StudentTask.vue`
- Modify: `frontend/src/pages/student/StudentInvitations.vue`
- Modify: `frontend/src/pages/student/PublicCaseApplication.vue`
- Modify: `frontend/src/pages/shared/ContentLibrary.vue`
- Modify: `frontend/src/router.ts`
- Test: `frontend/src/publicAuthStyles.test.ts`
- Test: `frontend/src/routeLifecycleUI.test.ts`
- Create: `frontend/src/studentPortalFlows.test.ts`

- [ ] **Step 1: Write failing fixture and flow tests**

在 `studentPortalModel.test.ts` 覆盖：多个项目、当前项目切换、归档项目隐藏、回收站 30 天倒计时、研究步骤状态和必填实验日志。

```ts
it('uses the selected current project for hero and AI context', () => {
  const model = buildStudentPortalModel(studentFixture)
  expect(model.currentProject.id).toBe(8)
  expect(model.aiContext.projectId).toBe(8)
})

it('blocks submission when an experimental step has no required log', () => {
  const task = buildTask({ status: 'in_progress', requiredMaterials: [{ kind: 'experiment_log', completed: false }] })
  expect(canSubmitTask(task)).toBe(false)
})
```

在 `studentPortalFlows.test.ts` 覆盖直接开题创建、AI 开题确认创建、项目归档/回收站/恢复、材料提交提示和校内成果申请入口；所有动作使用 fixture handler，不调用真实写接口。

- [ ] **Step 2: Run the tests and verify they fail**

Run: `npm --prefix frontend test -- --run src/studentPortalModel.test.ts src/studentPortalFlows.test.ts src/publicAuthStyles.test.ts src/routeLifecycleUI.test.ts`

Expected: FAIL because the fixture model, notification page and full student route states are not implemented.

- [ ] **Step 3: Add deterministic fixture data and state selectors**

`portalFixtures.ts` 提供一个学校、三个学生项目、一个待认领项目、步骤状态、材料版本、实验日志缺失、教师意见、邀请、学校通知和已发布案例。所有日期固定为 `2026-08-25`，不得调用 `Date.now()` 生成截图不稳定内容。

该文件同时导出页面模型使用的最小结构：

```ts
export interface StudentFixture {
  currentProjectId: number | null
  projects: Array<{ id: number; title: string; status: 'unclaimed' | 'active' | 'completed' | 'archived' | 'trashed'; trashedAt?: string }>
  tasks: Array<{ id: number; projectId: number; status: string; requiredMaterials: Array<{ kind: 'standard' | 'experiment_log'; completed: boolean }> }>
  notifications: Array<{ id: number; kind: string; title: string; isRead: boolean }>
}

export interface StudentTaskViewModel {
  status: string
  requiredMaterials: Array<{ kind: 'standard' | 'experiment_log'; completed: boolean }>
}
```

`studentPortalModel.ts` 导出：

```ts
export function buildStudentPortalModel(input: StudentFixture): StudentPortalModel
export function canSubmitTask(task: StudentTaskViewModel): boolean
export function daysUntilPurge(trashedAt: string, now: string): number
```

- [ ] **Step 4: Implement public and student pages against the model**

公共页面使用 `PublicShell`；学生页面使用 `StudentPortalShell`。首页 Hero 默认展示当前项目、项目进度、最近材料和下一步；项目页显示“直接填写开题报告”和“进入开题 AI”两条路径；研究旅程显示模板下载、上传、实验日志模板、审核状态和修改建议；材料档案显示已完成步骤的文字和文件；邀请、成果申请、赛事、公告和通知显示 loading/empty/error/disabled 状态。

在 `StudentNotifications.vue` 增加未读筛选、全部已读和通知详情跳转。页面继续使用确定性 fixture，所有写按钮先发出本地事件并显示确认反馈，直到 Task 10 接入 API。

- [ ] **Step 5: Run the fixture UI tests and build**

Run: `npm --prefix frontend test -- --run src/studentPortalModel.test.ts src/studentPortalFlows.test.ts src/publicAuthStyles.test.ts src/routeLifecycleUI.test.ts && npm --prefix frontend run build`

Expected: PASS and production build succeeds.

- [ ] **Step 6: Commit public/student fixture UI**

```bash
git add frontend/src/fixtures frontend/src/stores/studentPortalModel.ts frontend/src/stores/studentPortalModel.test.ts frontend/src/pages/public frontend/src/pages/student frontend/src/pages/shared/ContentLibrary.vue frontend/src/router.ts frontend/src/studentPortalFlows.test.ts frontend/src/publicAuthStyles.test.ts frontend/src/routeLifecycleUI.test.ts
git commit -m "feat: build public and student portal flows"
```

## Task 4: 重做灵思 AI 中心对话工作台

**Files:**
- Create: `frontend/src/components/ai/AIModeTabs.vue`
- Create: `frontend/src/components/ai/AIWorkbenchComposer.vue`
- Create: `frontend/src/components/ai/AIContextDrawer.vue`
- Create: `frontend/src/components/ai/AIDraftActions.vue`
- Create: `frontend/src/stores/aiWorkbenchModel.ts`
- Create: `frontend/src/stores/aiWorkbenchModel.test.ts`
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/components/ai/AIContextChooser.vue`
- Modify: `frontend/src/components/ai/AIToolPicker.vue`
- Modify: `frontend/src/components/ai/AIConversationHistory.vue`
- Modify: `frontend/src/components/ai/AIProjectAssistant.vue`
- Modify: `frontend/src/components/ai/AIResearchWizard.vue`
- Modify: `frontend/src/stores/aiConversationModel.ts`
- Test: `frontend/src/aiCenterUI.test.ts`
- Test: `frontend/src/studentAICenterEntry.test.ts`
- Test: `frontend/src/stores/aiConversationModel.test.ts`

- [ ] **Step 1: Write failing AI workspace tests**

在 `aiWorkbenchModel.test.ts` 固定三类、Agent 分类、项目上下文和写入边界：

```ts
it('maps research and defense to the current project', () => {
  expect(resolveAIContext('research', 8).projectId).toBe(8)
  expect(resolveAIContext('defense', 8).projectId).toBe(8)
})

it('keeps opening project-free', () => {
  expect(resolveAIContext('opening', 8).projectId).toBeNull()
})

it('requires an explicit action for business writes', () => {
  expect(draftActions('completed')).toEqual(['save_material', 'create_project_from_opening'])
})
```

在 `aiCenterUI.test.ts` 固定 DOM 结构：模式标签、Agent 标签、中心大对话区、上下文抽屉、引用来源、草稿核验项和显式保存按钮；不允许默认出现“自动保存到材料”。

- [ ] **Step 2: Run the AI tests and verify they fail**

Run: `npm --prefix frontend test -- --run src/stores/aiWorkbenchModel.test.ts src/aiCenterUI.test.ts src/studentAICenterEntry.test.ts`

Expected: FAIL because current页面仍以旧的场景选择/分步向导为主。

- [ ] **Step 3: Implement the AI state model**

`aiWorkbenchModel.ts` 导出：

```ts
export type AIWorkspaceMode = 'opening' | 'research' | 'defense'
export function resolveAIContext(mode: AIWorkspaceMode, currentProjectId: number | null): { projectId: number | null; scope: 'none' | 'current_project' }
export function visibleAgents(mode: AIWorkspaceMode, agents: AIAgent[]): AIAgent[]
export function draftActions(status: string): Array<'save_material' | 'create_project_from_opening'>
```

`AICenter.vue` 的模式切换只改变 Agent 和上下文，不改变既有对话历史；切换到研究/答辩且没有当前项目时，显示选择项目或回到开题的空状态。

- [ ] **Step 4: Implement the WorkBuddy-like composition**

中心区域使用大对话框、消息流、快捷问题、输入框和发送状态；顶部显示“开题 / 研究 / 答辩”，下方显示 Agent；上下文抽屉显示当前项目、读取材料数、来源和“只读草稿”提示。保留 SSE、重试、历史会话和归档功能。

开题消息显示结构化开题报告预览和“用此报告创建项目”；研究/答辩消息显示草稿、来源、核验项和“保存为材料”；两类动作都必须经过确认对话框。教师审核 Agent 入口继续由教师审核页面调用，不复用学生写材料动作。

- [ ] **Step 5: Run AI unit tests and build**

Run: `npm --prefix frontend test -- --run src/stores/aiWorkbenchModel.test.ts src/aiCenterUI.test.ts src/studentAICenterEntry.test.ts src/stores/aiConversationModel.test.ts && npm --prefix frontend run build`

Expected: PASS and build succeeds.

- [ ] **Step 6: Commit AI workbench UI**

```bash
git add frontend/src/components/ai frontend/src/pages/shared/AICenter.vue frontend/src/stores/aiWorkbenchModel.ts frontend/src/stores/aiWorkbenchModel.test.ts frontend/src/stores/aiConversationModel.ts frontend/src/aiCenterUI.test.ts frontend/src/studentAICenterEntry.test.ts frontend/src/stores/aiConversationModel.test.ts
git commit -m "feat: redesign lingsu ai workbench"
```

## Task 5: 完成教师端和平台端 fixture-first 页面

**Files:**
- Create: `frontend/src/fixtures/managementFixtures.ts`
- Create: `frontend/src/stores/managementPortalModel.ts`
- Create: `frontend/src/stores/managementPortalModel.test.ts`
- Create: `frontend/src/pages/teacher/TeacherNotifications.vue`
- Modify: `frontend/src/pages/teacher/TeacherWorkbench.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectDetail.vue`
- Modify: `frontend/src/pages/teacher/TeacherProjectTemplate.vue`
- Modify: `frontend/src/pages/teacher/TeacherAnnouncements.vue`
- Modify: `frontend/src/pages/platform/PlatformConsole.vue`
- Modify: `frontend/src/pages/platform/PlatformAIAgents.vue`
- Modify: `frontend/src/pages/platform/PlatformCases.vue`
- Modify: `frontend/src/pages/platform/PlatformSettings.vue`
- Modify: `frontend/src/pages/platform/SchoolDetail.vue`
- Modify: `frontend/src/router.ts`
- Test: `frontend/src/teacherPoolStyles.test.ts`
- Test: `frontend/src/teacherAIReviewUI.test.ts`
- Test: `frontend/src/platformAgentsStyles.test.ts`
- Test: `frontend/src/platformLicenseStyles.test.ts`
- Test: `frontend/src/managementPortalModel.test.ts`

- [ ] **Step 1: Write failing management tests**

覆盖以下状态：待认领项目、已被其他教师认领、本人指导项目待审核、非本人项目无审核按钮、平台学校授权开关、AI 模板启停、案例待平台审核和学校通知发布。

```ts
it('hides review actions for projects not guided by the current teacher', () => {
  expect(reviewActions({ primaryTeacherId: 11, currentTeacherId: 12 })).toEqual([])
})

it('shows platform case review only after student consent', () => {
  expect(caseStatus({ teacherInvite: true, studentConsent: false })).toBe('waiting_student')
})
```

- [ ] **Step 2: Run management tests and verify they fail**

Run: `npm --prefix frontend test -- --run src/managementPortalModel.test.ts src/teacherPoolStyles.test.ts src/teacherAIReviewUI.test.ts src/platformAgentsStyles.test.ts src/platformLicenseStyles.test.ts`

Expected: FAIL because the fixture model and full permission states are not present.

- [ ] **Step 3: Implement management ViewModels and pages**

`managementPortalModel.ts` 提供 `reviewActions`、`caseStatus`、`poolRows`、`schoolOverview` 和 `agentTemplateRows`。教师工作台按本校项目汇总，项目池显示开题细则和“认领”状态；材料审核只在 `primaryTeacherId === currentTeacherId` 时显示通过/打回。平台端不把低频设置塞入概览，学校名进入详情，授权开关只改变授权状态。

这些选择器使用固定输入输出：

```ts
export function reviewActions(input: { primaryTeacherId: number | null; currentTeacherId: number }): string[]
export function caseStatus(input: { teacherInvite: boolean; studentConsent: boolean; platformReview: boolean }): 'waiting_student' | 'pending_platform' | 'published'
```

新增教师通知页面；教师成果申请页区分学生校内申请和教师公域邀请。平台案例页显示学生同意、指导教师审核和平台审核三段状态。

- [ ] **Step 4: Run tests and build**

Run: `npm --prefix frontend test -- --run src/managementPortalModel.test.ts src/teacherPoolStyles.test.ts src/teacherAIReviewUI.test.ts src/platformAgentsStyles.test.ts src/platformLicenseStyles.test.ts && npm --prefix frontend run build`

Expected: PASS and build succeeds.

- [ ] **Step 5: Commit management fixture UI**

```bash
git add frontend/src/fixtures/managementFixtures.ts frontend/src/stores/managementPortalModel.ts frontend/src/stores/managementPortalModel.test.ts frontend/src/pages/teacher frontend/src/pages/platform frontend/src/router.ts frontend/src/teacherPoolStyles.test.ts frontend/src/teacherAIReviewUI.test.ts frontend/src/platformAgentsStyles.test.ts frontend/src/platformLicenseStyles.test.ts
git commit -m "feat: build teacher and platform management views"
```

## Task 6: 补齐后端领域字段、序列化和权限接口

**Files:**
- Modify: `backend/apps/core/models.py`
- Create: `backend/apps/core/migrations/0037_functional_rearchitecture.py`
- Modify: `backend/apps/core/serializers.py`
- Modify: `backend/apps/core/views.py`
- Modify: `backend/apps/core/urls.py`
- Modify: `backend/apps/core/workflows/projects.py`
- Modify: `backend/apps/core/workflows/materials.py`
- Modify: `backend/apps/core/workflows/cases.py`
- Create: `backend/apps/core/tests/test_functional_contract.py`
- Modify: `backend/apps/core/tests/test_project_lifecycle.py`
- Modify: `backend/apps/core/tests/test_template_blueprint.py`
- Modify: `backend/apps/core/tests/test_public_cases.py`
- Modify: `backend/apps/core/tests/test_write_boundaries.py`

- [ ] **Step 1: Write failing backend contract tests**

在 `test_functional_contract.py` 的 `setUp` 中建立两个教师、一个学生、一个已认领项目、一个待审核材料版本和一个教师公域展示申请工厂；`make_teacher_public_case(student_consent_at=None)` 必须创建 `request_type="teacher_platform"`、`visibility_scope="platform"` 的申请。增加：

```python
def test_experiment_log_is_required_before_task_submit(self):
    response = self.client.post(f"/api/material-revisions/{self.revision.id}/submit/", {"truth_confirmed": True})
    self.assertEqual(response.status_code, 400)
    self.assertIn("实验日志", response.json()["detail"])

def test_teacher_cannot_review_a_project_guided_by_another_teacher(self):
    self.client.force_login(self.other_teacher)
    response = self.client.post(f"/api/material-revisions/{self.revision.id}/review/", {"outcome": "approved", "comment": "ok"})
    self.assertEqual(response.status_code, 403)

def test_student_case_requires_student_consent_before_platform_publication(self):
    case = self.make_teacher_public_case(student_consent_at=None)
    response = self.client.post(f"/api/public-case-requests/{case.id}/set_visibility/", {"visible": True})
    self.assertEqual(response.status_code, 400)
```

在现有项目生命周期测试中补充归档长期保留、回收站恢复和多项目 current project 的断言。

- [ ] **Step 2: Run the backend tests and verify they fail**

Run: `docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_functional_contract apps.core.tests.test_project_lifecycle apps.core.tests.test_public_cases apps.core.tests.test_write_boundaries`

Expected: FAIL because the experiment-log kind, case consent flow and new notification/status fields do not exist.

- [ ] **Step 3: Add the minimum model fields and migration**

在 `TemplateMaterial` 和 `Material` 增加 `kind`，取值 `standard` / `experiment_log`，默认 `standard`；模板实例化时复制该值。对 `AIConversation` 增加 `workspace_mode`，取值 `opening` / `research` / `defense`；对 `AIGenerationLog.project` 允许为空，以便结构化开题生成拥有项目级审计记录前仍可保存会话草稿。

对 `PublicCaseRequest` 增加 `request_type`（`student_school` / `teacher_platform`）、`visibility_scope`（`school` / `platform`）、`student_consent_at`、`student_consent_by` 和 `platform_reviewer`；状态增加 `waiting_student` 和 `pending_platform`。学生校内申请在指导教师通过后使用 `published + school`，教师公域申请必须经过 `waiting_student → pending_platform → published + platform`。对 `Notification.Kind` 增加学校通知、平台公告、邀请待处理、审核建议和案例待同意等类型；对 `AuditEvent.Action` 增加 AI 草稿确认保存、学生同意公域展示和项目清理动作。

生成并检查迁移：

```bash
docker exec lingsu-backend-1 python manage.py makemigrations core
docker exec lingsu-backend-1 python manage.py makemigrations --check --dry-run
```

提交的迁移文件必须与 `0037_functional_rearchitecture.py` 内容一致，不编辑历史迁移。

- [ ] **Step 4: Implement serializers and endpoints**

在 `serializers.py` 输出 `kind`、`workspace_mode`、案例同意链和 purge 倒计时；在 `views.py` 保留现有 `set_primary`，补充显式 API：

```text
POST /api/projects/{id}/set_primary/
POST /api/projects/{id}/create_from_opening/
POST /api/material-revisions/{id}/submit/
POST /api/public-case-requests/{id}/student_consent/
POST /api/public-case-requests/{id}/teacher_invite/
POST /api/public-case-requests/{id}/platform_review/
```

所有动作按当前用户学校、项目成员、项目负责人、指导教师和平台管理员校验；禁止使用前端传入的 `school`、`applicant`、`teacher_reviewer` 或 `admin_reviewer` 覆盖服务器身份。

- [ ] **Step 5: Run migrations and backend tests**

Run:

```bash
docker exec lingsu-backend-1 python manage.py migrate
docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_functional_contract apps.core.tests.test_project_lifecycle apps.core.tests.test_template_blueprint apps.core.tests.test_public_cases apps.core.tests.test_write_boundaries
```

Expected: migration succeeds and all targeted tests pass.

- [ ] **Step 6: Commit the domain contract**

```bash
git add backend/apps/core/models.py backend/apps/core/migrations/0037_functional_rearchitecture.py backend/apps/core/serializers.py backend/apps/core/views.py backend/apps/core/urls.py backend/apps/core/workflows/projects.py backend/apps/core/workflows/materials.py backend/apps/core/workflows/cases.py backend/apps/core/tests/test_functional_contract.py backend/apps/core/tests/test_project_lifecycle.py backend/apps/core/tests/test_template_blueprint.py backend/apps/core/tests/test_public_cases.py backend/apps/core/tests/test_write_boundaries.py
git commit -m "feat: enforce lingsu project workflow contracts"
```

## Task 7: 实现三类 AI、项目上下文和显式写入后端

**Files:**
- Modify: `backend/apps/core/models.py`
- Modify: `backend/apps/core/serializers.py`
- Modify: `backend/apps/core/views.py`
- Modify: `backend/apps/core/ai_agents.py`
- Modify: `backend/apps/core/tasks.py`
- Modify: `backend/apps/core/workflows/ai.py`
- Modify: `backend/apps/core/management/commands/seed_ai_agents.py`
- Create: `backend/apps/core/tests/test_ai_workspace_contract.py`
- Modify: `backend/apps/core/tests/test_ai_conversations.py`
- Modify: `backend/apps/core/tests/test_agents.py`
- Modify: `backend/apps/core/tests/test_ai_service.py`

- [ ] **Step 1: Write failing AI contract tests**

覆盖：

- 开题对话 `workspace_mode=opening` 不绑定项目，可以生成结构化开题草稿。
- 研究/答辩没有当前项目时返回明确的选择项目错误，不读取任意项目。
- 当前项目读取只包含当前项目的材料、附件提取文字和教师意见。
- AI 生成完成不会创建 `MaterialRevision`；只有显式 `save_as_material` 才创建。
- 学生明确确认开题草稿后才能创建项目。
- 教师 AI 不能读取非本人负责项目。

测试至少包含以下请求断言：

```python
conversation = AIConversation.objects.create(owner=self.student, workspace_mode="opening")
response = self.post_message(conversation, agent_key="proposal-topic", project=None)
self.assertEqual(response.status_code, 201)
self.assertIsNone(response.data.get("generation_log"))
```

- [ ] **Step 2: Run the AI tests and verify they fail**

Run: `docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_ai_workspace_contract apps.core.tests.test_ai_conversations apps.core.tests.test_agents apps.core.tests.test_ai_service`

Expected: FAIL on mode validation, project-free structured logs and explicit consent checks.

- [ ] **Step 3: Normalize Agent templates**

在 `seed_ai_agents.py` 中将全局 Agent 的顶层分类固定为 `opening`、`research`、`defense`；研究和答辩分类下配置科创 Agent、实验日志、材料完善、研究报告、答辩提纲和问答模拟；教师模板使用 `role=teacher` 和审核上下文。保留旧 key 的兼容映射，避免历史会话打不开。

在 `ai_agents.py` 增加模式与 Agent 的兼容校验：`opening` 只能使用项目为空的开题 Agent；`research/defense` 必须拥有当前项目；模板的 `context_scope_default` 决定可读取范围，客户端不能扩大范围。

- [ ] **Step 4: Implement context and write boundaries**

调整 `AIGenerationLog.project` 的空值处理；`create_ai_request`、Celery 任务和 SSE 事件都携带 `workspace_mode`。引用来源统一写入 `referenced_sources`，包括步骤、材料、附件和教师反馈。

保留 `save_as_material` 作为显式写入入口，并新增 `create_from_opening` 的确认校验：只有当前学生、当前无项目绑定的开题会话、完成的结构化草稿和明确 `confirm=true` 才能创建项目；重复请求返回同一项目或明确冲突，不重复创建。

- [ ] **Step 5: Run targeted AI tests and seed validation**

Run:

```bash
docker exec lingsu-backend-1 python manage.py seed_ai_agents --reset
docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_ai_workspace_contract apps.core.tests.test_ai_conversations apps.core.tests.test_agents apps.core.tests.test_ai_service
```

Expected: seed is idempotent and all AI tests pass.

- [ ] **Step 6: Commit AI backend**

```bash
git add backend/apps/core/models.py backend/apps/core/serializers.py backend/apps/core/views.py backend/apps/core/ai_agents.py backend/apps/core/tasks.py backend/apps/core/workflows/ai.py backend/apps/core/management/commands/seed_ai_agents.py backend/apps/core/tests/test_ai_workspace_contract.py backend/apps/core/tests/test_ai_conversations.py backend/apps/core/tests/test_agents.py backend/apps/core/tests/test_ai_service.py
git commit -m "feat: add scoped lingsu ai workspace modes"
```

## Task 8: 完成材料审核、通知、成果展示和回收站清理

**Files:**
- Modify: `backend/apps/core/workflows/materials.py`
- Modify: `backend/apps/core/workflows/cases.py`
- Modify: `backend/apps/core/views.py`
- Modify: `backend/apps/core/tasks.py`
- Modify: `backend/apps/core/notifiers/__init__.py`
- Create: `backend/apps/core/management/commands/purge_trashed_projects.py`
- Create: `backend/apps/core/tests/test_research_material_requirements.py`
- Create: `backend/apps/core/tests/test_case_consent_flow.py`
- Create: `backend/apps/core/tests/test_trash_purge.py`
- Modify: `backend/apps/core/tests/test_notifications.py`
- Modify: `backend/apps/core/tests/test_workflow_audit.py`

- [ ] **Step 1: Write failing workflow tests**

覆盖以下完整链路：

1. 实验相关步骤缺少 `kind=experiment_log` 的已填写材料时，提交返回 400，且不改变 revision 状态。
2. 教师通过或打回只作用于自己负责项目；打回必须有非空建议。
3. 学生校内申请可由指导教师处理，但不进入公域发布状态。
4. 教师公域邀请先进入 `waiting_student`，学生同意后才进入 `pending_platform`，平台通过后才变为 `published`。
5. 回收站项目在 30 天内可恢复，超过 30 天删除附件、AI 会话、导出文件并留下审计摘要。
6. 学校通知只为本校学生和教师生成通知，平台公告可以被公共入口读取。

- [ ] **Step 2: Run workflow tests and verify they fail**

Run: `docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_research_material_requirements apps.core.tests.test_case_consent_flow apps.core.tests.test_trash_purge apps.core.tests.test_notifications apps.core.tests.test_workflow_audit`

Expected: FAIL on log enforcement, consent transitions and purge behavior.

- [ ] **Step 3: Enforce step-level experiment logs and immutable revisions**

在 `submit_material_revision` 中按项目步骤读取所有 required materials；若该步骤存在实验日志模板且没有有效草稿/已提交/已通过日志，则返回包含材料标题的结构化错误。审核继续使用不可覆盖的 `MaterialRevision`，新修改创建新版本。

- [ ] **Step 4: Implement case consent and notification transitions**

在 `cases.py` 中把学生校内申请与教师公域邀请区分为不同 `request_type`；新增学生同意动作、平台待审核动作和平台发布动作。每次转换创建相应通知和审计事件，禁止客户端直接传入最终状态。

- [ ] **Step 5: Implement deterministic purge**

`purge_trashed_projects` 命令按 `trashed_at <= now - timedelta(days=30)` 查询；先删除私有文件和相关上传临时文件，再删除业务关联，最后写入包含项目 ID、标题、学校、清理时间的不可恢复审计摘要。命令支持 dry-run 输出数量，Celery Beat 每日调用同一服务函数，避免命令和任务分叉。

Run: `docker exec lingsu-backend-1 python manage.py purge_trashed_projects --dry-run`

Expected: 只输出到期数量，不删除任何记录。

- [ ] **Step 6: Run targeted workflows and commit**

```bash
docker exec lingsu-backend-1 python manage.py test apps.core.tests.test_research_material_requirements apps.core.tests.test_case_consent_flow apps.core.tests.test_trash_purge apps.core.tests.test_notifications apps.core.tests.test_workflow_audit
git add backend/apps/core/workflows/materials.py backend/apps/core/workflows/cases.py backend/apps/core/views.py backend/apps/core/tasks.py backend/apps/core/notifiers backend/apps/core/management/commands/purge_trashed_projects.py backend/apps/core/tests/test_research_material_requirements.py backend/apps/core/tests/test_case_consent_flow.py backend/apps/core/tests/test_trash_purge.py backend/apps/core/tests/test_notifications.py backend/apps/core/tests/test_workflow_audit.py
git commit -m "feat: complete material case notification workflows"
```

## Task 9: 接入独立项目控制台和服务验收

**Files:**
- Modify: `scripts/project-console.py`
- Modify: `scripts/console.sh`
- Modify: `scripts/console.html`
- Modify: `scripts/test_project_console.py`
- Modify: `docs/项目运行说明.md`

- [ ] **Step 1: Add failing console lifecycle tests**

在 `test_project_console.py` 增加：

- 从 `PORT=8801 ./scripts/console.sh` 启动时只改变控制台端口，不改变项目端口。
- `/api/status` 返回 `runtime=host`、`managed_by_docker=false` 和服务状态。
- 项目 stop/restart 和 Colima stop/restart 没有确认字段时返回 400。
- 控制台停止项目后仍能读取 `/api/status` 和 `/api/logs`。
- `docker-compose.yml` 不包含 console service。
- HTML 不包含角色切换文案、持久化底部 tips 或 Demo 提示。

- [ ] **Step 2: Run console tests and verify failures**

Run: `python3 -m unittest scripts/test_project_console.py -v`

Expected: newly added lifecycle tests fail until script and UI behavior are aligned.

- [ ] **Step 3: Implement host-process guardrails**

`console.sh` 使用脚本所在目录计算项目根目录，不依赖当前工作目录；保留 `PORT` 环境变量；退出 Docker/项目命令时不结束 Python 服务。`project-console.py` 对 action target/service 使用白名单，对停止/重启操作要求 `confirm=true`，日志 service 使用固定服务集合。

- [ ] **Step 4: Align console UI with management design**

`console.html` 使用 66px 顶栏、232px 侧栏、指标卡、服务卡片、日志面板和健康验收区；不显示“项目控制台 · 概览”、角色 chip、侧栏提示和底部提示。所有启停动作显示当前状态、二次确认和操作结果。

- [ ] **Step 5: Run console tests and independent-process smoke test**

Run:

```bash
python3 -m unittest scripts/test_project_console.py -v
PORT=8801 ./scripts/console.sh
```

在第二个终端调用 `/api/status`，再通过 `/api/action` 停止项目，确认 8801 端口仍能返回状态和日志；结束测试时只停止本次 8801 控制台进程，不停止用户现有项目服务。

- [ ] **Step 6: Commit console changes**

```bash
git add scripts/project-console.py scripts/console.sh scripts/console.html scripts/test_project_console.py docs/项目运行说明.md
git commit -m "feat: harden independent lingsu project console"
```

## Task 10: 用真实 API 替换 fixture 并补齐写操作反馈

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/stores/auth.ts`
- Modify: `frontend/src/stores/studentApiModel.ts`
- Modify: `frontend/src/stores/teacherApiModel.ts`
- Modify: `frontend/src/stores/platformApiModel.ts`
- Modify: `frontend/src/stores/aiConversationModel.ts`
- Modify: `frontend/src/pages/student/StudentProjects.vue`
- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/pages/student/StudentTask.vue`
- Modify: `frontend/src/pages/student/StudentInvitations.vue`
- Modify: `frontend/src/pages/student/PublicCaseApplication.vue`
- Modify: `frontend/src/pages/student/StudentNotifications.vue`
- Modify: `frontend/src/pages/shared/AICenter.vue`
- Modify: `frontend/src/pages/teacher/TeacherWorkbench.vue`
- Modify: `frontend/src/pages/platform/PlatformCases.vue`
- Modify: `frontend/src/pages/platform/PlatformAIAgents.vue`
- Modify: `frontend/src/pages/platform/PlatformSettings.vue`
- Modify: `frontend/src/components/FeedbackBanner.vue`
- Modify: `frontend/src/components/ConfirmDialog.vue`
- Modify: `frontend/src/components/EmptyState.vue`
- Modify: `frontend/src/components/TaskStatusCard.vue`
- Modify: `frontend/src/components/ProjectLifecycleMenu.vue`
- Modify: `frontend/src/api.test.ts`

- [ ] **Step 1: Add failing API contract tests**

在 `api.test.ts` 固定请求方法、路径和 payload：`set_primary`、`archive/trash/restore`、材料提交/审核、AI 显式保存、开题创建项目、学生同意成果、教师公域邀请、平台案例审核、通知 read/all-read。

- [ ] **Step 2: Run API tests and verify failures**

Run: `npm --prefix frontend test -- --run src/api.test.ts`

Expected: FAIL for newly named endpoints or incorrect payloads.

- [ ] **Step 3: Replace fixture handlers with API calls**

每个写操作都实现 `loading → success → error` 三态；失败时保留用户输入和草稿，不重置整个页面。删除、回收站、发布、平台授权、教师审核和 AI 保存都使用 `ConfirmDialog`；没有权限时隐藏写按钮并提供只读解释。

保留 fixture 作为 API 失败的明确 empty/error 视觉数据，不在生产模式静默伪造成功。

- [ ] **Step 4: Run frontend unit tests and production build**

Run: `npm --prefix frontend test && npm --prefix frontend run build`

Expected: all existing and newly added frontend tests pass; `vue-tsc` and Vite build succeed.

- [ ] **Step 5: Commit real API integration**

```bash
git add frontend/src/api.ts frontend/src/stores frontend/src/pages frontend/src/components/FeedbackBanner.vue frontend/src/components/ConfirmDialog.vue frontend/src/components/EmptyState.vue frontend/src/components/TaskStatusCard.vue frontend/src/components/ProjectLifecycleMenu.vue frontend/src/api.test.ts
git commit -m "feat: connect lingsu portals to real workflows"
```

## Task 11: 全路由 E2E、截图矩阵和最终验收

**Files:**
- Create: `frontend/e2e/full-functional.spec.ts`
- Modify: `frontend/e2e/full-site-visual.spec.ts`
- Modify: `frontend/e2e/mvp.spec.ts`
- Modify: `scripts/lingsu-e2e.mjs`
- Modify: `docs/MVP验收清单.md`
- Modify: `design-qa.md`

- [ ] **Step 1: Add failing end-to-end scenarios**

`full-functional.spec.ts` 必须覆盖：

1. 公共入口 → 注册/登录 → 按角色进入工作台。
2. 学生直接填写开题报告创建项目 → 当前项目切换 → Hero 显示当前项目。
3. 学生进入开题 AI → 生成草稿 → 明确确认 → 创建项目；未确认不创建。
4. 教师项目池查看开题 → 原子认领 → 只有本人看到审核操作。
5. 学生填写材料和实验日志 → 提交审核 → 教师通过/打回 → 学生看到建议并创建新版本。
6. AI 研究模式读取当前项目，切换其他项目后上下文变化，不能读取原项目。
7. 学生校内成果申请；教师公域邀请；学生同意；平台审核发布。
8. 学生回收项目并在 30 天内恢复；控制台独立启动后停止项目，控制台状态仍可用。

视觉测试在 1280px 和 1440px 对公共、学生首页、学生 AI、教师工作台、教师审核、平台概览、平台案例、控制台各捕获一张稳定状态截图。

基础测试结构固定为：

```ts
test('student can confirm an opening draft before creating a project', async ({ page }) => {
  await page.goto('/student/ai?mode=opening')
  await page.getByRole('button', { name: '用此报告创建项目' }).click()
  await expect(page.getByRole('dialog')).toContainText('确认创建项目')
  await page.getByRole('button', { name: '确认创建' }).click()
  await expect(page).toHaveURL(/\/student\/projects\/\d+\/map/)
})
```

- [ ] **Step 2: Run E2E and capture the first matrix**

Run: `npm --prefix frontend run test:e2e -- --project=chromium`

Expected: new tests initially expose missing seeded data, route guards or selectors; record each failure by route and state before fixing.

- [ ] **Step 3: Fix selectors and state setup without weakening assertions**

使用 `data-testid` 或稳定可访问名称，不使用坐标点击和随机文本；测试数据通过现有 demo seed/后端 fixture 建立。不要把断言改成“页面可加载”来绕过权限、状态或写入失败。

- [ ] **Step 4: Run visual and overflow checks**

对每个目标路由执行：字体/标题为系统无衬线；顶栏高度一致；教师/平台侧栏 232px；公共/学生无侧栏；页面 `scrollWidth` 不超过 viewport；卡片、按钮、状态、圆角、边框、阴影和间距来自共享令牌。

- [ ] **Step 5: Run complete verification**

```bash
npm --prefix frontend test
npm --prefix frontend run build
npm --prefix frontend run test:e2e -- --project=chromium
docker exec lingsu-backend-1 python manage.py makemigrations --check --dry-run
docker exec lingsu-backend-1 python manage.py test apps
python3 -m unittest scripts/test_project_console.py -v
```

Expected: all tests pass, no unapplied migrations, production build succeeds, E2E covers every listed role flow, and console tests confirm the host-process boundary.

- [ ] **Step 6: Commit final verification artifacts**

```bash
git add frontend/e2e/full-functional.spec.ts frontend/e2e/full-site-visual.spec.ts frontend/e2e/mvp.spec.ts scripts/lingsu-e2e.mjs docs/MVP验收清单.md design-qa.md
git commit -m "test: verify lingsu full product workflows"
```

## Spec coverage review

- 公共入口全屏、登录注册、公开案例和指引：Tasks 2–3、10–11。
- 学生多项目、当前项目、项目创建、归档/回收站、研究旅程、材料、实验日志、邀请、成果申请、赛事通知：Tasks 1–3、6、8、10–11。
- 灵思 AI 三类、科创 Agent、WorkBuddy 中心对话、项目上下文、引用、显式写入：Tasks 4、7、10–11。
- 教师项目池、原子认领、指导项目、材料审核、审核 AI、学生管理、邀请、成果展示和学校通知：Tasks 5–8、10–11。
- 平台学校、授权、Agent 模板、赛事公告、案例治理和设置：Tasks 5–7、10–11。
- 独立控制台、Docker/Colima、服务状态、日志、健康检查和不随项目停止：Task 9、11。
- 统一方案 B UI、学生顶部导航、公共无侧栏、PC 1280/1440、无横向溢出：Tasks 2–5、11。

## Assumptions and defaults

- 项目只有一个指导教师；多教师协作如未来需要，新增协指导关系，不改变本计划的审核权限。
- 学生校内成果申请由指导教师处理并保持校内范围；教师发起的公域邀请需要学生同意和平台审核。
- AI 生成结果默认是会话草稿；显式保存材料或创建项目是唯一业务写入入口。
- 30 天清理按 `trashed_at` 计算；归档不会触发清理。
- 现有未提交修改属于用户，实施者必须逐任务避让；计划中的每个 commit 只包含对应任务文件。
