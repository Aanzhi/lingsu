# 灵溯学生项目闭环 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让学生在灵溯中真实完成创建立项申请、等待审批、编辑开题草稿与确认后提交审核。

**Architecture:** Django 增加当前用户端点和 Proposal 指导教师关联，并收紧项目列表/审批权限；使用已有 Material/MaterialRevision 状态机保存材料。Vue 增加学生 API 客户端与一个项目流程状态模块，再把学生工作台替换为 API 驱动的抽屉表单和开题编辑器。

**Tech Stack:** Django、Django REST Framework、Django TestCase；Vue 3、TypeScript、Element Plus、Axios、Vitest。

---

### Task 1: 后端学生项目权限与当前用户接口

**Files:**
- Modify: `backend/apps/core/models.py`
- Modify: `backend/apps/core/serializers.py`
- Modify: `backend/apps/core/views.py`
- Modify: `backend/apps/core/urls.py`
- Create: `backend/apps/core/migrations/0003_proposal_teacher.py`
- Modify: `backend/apps/core/tests/test_workflows.py`

- [ ] **Step 1: 先写失败测试：`/api/me/` 返回当前角色；学生只能列出自己参加的项目；立项申请需要同校教师。**

```python
def test_student_project_scope_me_and_teacher_bound_proposal(self):
    school = School.objects.create(name="学生流程学校")
    teacher = Account.objects.create_user(username="guide", school=school, role="teacher")
    student = Account.objects.create_user(username="student-flow", school=school, role="student")
    other_student = Account.objects.create_user(username="other-flow", school=school, role="student")
    own = Project.objects.create(school=school, title="我的项目", leader=student, primary_teacher=teacher)
    own.members.create(account=student, role="leader")
    Project.objects.create(school=school, title="别人的项目", leader=other_student, primary_teacher=teacher)
    client = APIClient(); client.force_authenticate(student)
    self.assertEqual(client.get('/api/me/').data['role'], 'student')
    self.assertEqual([p['title'] for p in client.get('/api/projects/').data], ['我的项目'])
    response = client.post('/api/proposals/', {'title':'节水','problem':'浪费','plan':'测试方案','teacher':teacher.id}, format='json')
    self.assertEqual(response.status_code, 201)
```

- [ ] **Step 2: 运行目标测试，确认失败。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test apps.core.tests -v 2`  
Expected: FAIL，`/api/me/` 返回 404、`teacher` 字段不存在或项目列表包含别人的项目。

- [ ] **Step 3: 实现最小安全接口。**

```python
class Proposal(SchoolBound):
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='guided_proposals')

class MeView(APIView):
    def get(self, request):
        user = request.user
        return Response({'id': user.id, 'username': user.username, 'role': user.role,
                         'school': user.school_id, 'must_change_password': user.must_change_password})

class ProjectViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        base = school_queryset(Project.objects.prefetch_related('members__account'), self.request.user)
        if self.request.user.role == 'student':
            return base.filter(Q(leader=self.request.user) | Q(members__account=self.request.user)).distinct()
        if self.request.user.role == 'teacher':
            return base.filter(primary_teacher=self.request.user)
        return base
```

`ProposalSerializer` 暴露 `teacher`，`perform_create` 校验该账号属于当前学校且角色为 teacher。`approve` 仅允许该申请 `teacher` 或 school_admin/super_admin，并把项目的 `primary_teacher` 设置为申请中的教师。路由添加 `path('me/', MeView.as_view())`。

- [ ] **Step 4: 生成迁移并运行全量后端检查。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py makemigrations core && /opt/anaconda3/bin/python3.12 manage.py test && /opt/anaconda3/bin/python3.12 manage.py check`  
Expected: 迁移增加 `Proposal.teacher`；测试和系统检查通过。

### Task 2: 学生流程前端 API 与状态模块

**Files:**
- Modify: `frontend/src/api.ts`
- Create: `frontend/src/stores/studentFlow.ts`
- Create: `frontend/src/stores/studentFlow.test.ts`

- [ ] **Step 1: 写失败测试：AI 预览在采用前不修改草稿，采用后写入草稿；真实性确认决定能否提交。**

```ts
import { describe, expect, it } from 'vitest'
import { adoptAiPreview, canSubmitRevision } from './studentFlow'

describe('student project flow', () => {
  it('adopts an AI preview only after the student chooses it', () => {
    expect(adoptAiPreview('已有内容', 'AI 建议')).toBe('已有内容\n\nAI 建议')
  })
  it('requires content and truth confirmation before submitting', () => {
    expect(canSubmitRevision('开题内容', false)).toBe(false)
    expect(canSubmitRevision('开题内容', true)).toBe(true)
  })
})
```

- [ ] **Step 2: 运行目标测试，确认失败。**

Run: `cd frontend && npm test -- studentFlow.test.ts`  
Expected: FAIL，提示模块不存在。

- [ ] **Step 3: 实现纯状态函数与 API 类型。**

```ts
export const adoptAiPreview = (draft: string, preview: string) =>
  [draft.trim(), preview.trim()].filter(Boolean).join('\n\n')
export const canSubmitRevision = (content: string, truthConfirmed: boolean) => Boolean(content.trim()) && truthConfirmed
```

在 `api.ts` 增加：

```ts
export type Me = { id: number; username: string; role: 'student' | 'teacher' | 'school_admin'; school: number | null }
export type Proposal = { id:number; title:string; problem:string; plan:string; teacher:number; status:string; project_id?:number }
export type Project = { id:number; title:string; summary:string; primary_teacher:number | null }
export type Material = { id:number; project:number; title:string; status:string; revisions: MaterialRevision[] }
export type MaterialRevision = { id:number; material:number; content:string; status:string; created_at:string }
export const getMe = () => api.get<Me>('/me/')
export const getProposals = () => api.get<Proposal[]>('/proposals/')
export const createProposal = (payload: Pick<Proposal, 'title'|'problem'|'plan'|'teacher'>) => api.post<Proposal>('/proposals/', payload)
export const getProjects = () => api.get<Project[]>('/projects/')
export const createMaterial = (project:number, title:string) => api.post<Material>('/materials/', { project, title })
export const createMaterialRevision = (material:number, content:string) => api.post<MaterialRevision>('/material-revisions/', { material, content })
export const submitMaterialRevision = (id:number) => api.post<MaterialRevision>(`/material-revisions/${id}/submit/`, { truth_confirmed: true })
```

- [ ] **Step 4: 运行前端单元测试。**

Run: `cd frontend && npm test`  
Expected: 原有 6 项测试及学生流程测试全部通过。

### Task 3: 学生立项、开题草稿与 AI 采用交互

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: 写失败测试，定义学生工作台的可执行状态。**

```ts
it('renders a pending proposal state before a project exists', () => {
  expect(studentDashboardState([], [{ status: 'pending' }]).mode).toBe('pending')
})
it('renders an editable project state after approval', () => {
  expect(studentDashboardState([{ id: 1 }], []).mode).toBe('project')
})
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `cd frontend && npm test -- studentFlow.test.ts`  
Expected: FAIL，`studentDashboardState` 未定义。

- [ ] **Step 3: 扩充流程状态并实现三段交互。**

新增 `studentDashboardState(projects, proposals)`，无项目且有 pending 为 `pending`，有项目为 `project`，否则为 `empty`。在学生工作台实现：

```vue
<el-drawer v-model="proposalOpen">
  <el-form :model="proposalForm" :rules="proposalRules">
    <el-form-item label="项目名称" prop="title"><el-input v-model="proposalForm.title" /></el-form-item>
    <el-form-item label="想解决的问题" prop="problem"><el-input v-model="proposalForm.problem" type="textarea" /></el-form-item>
    <el-form-item label="初步方案" prop="plan"><el-input v-model="proposalForm.plan" type="textarea" /></el-form-item>
    <el-form-item label="指导教师" prop="teacher"><el-select v-model="proposalForm.teacher" /></el-form-item>
  </el-form>
</el-drawer>
```

- `empty`：主按钮打开立项抽屉；提交 `createProposal`，成功后刷新 proposals 并切换 `pending` 状态。
- `pending`：显示“等待教师立项审核”、项目名称及提交说明；禁用开题提交操作。
- `project`：主卡显示“开题报告”、状态、编辑开题报告按钮。若材料不存在，点击编辑时先 `createMaterial(project.id, '开题报告')`，然后打开编辑抽屉。
- 编辑抽屉保存多行草稿；调用 `createMaterialRevision` 保存版本。AI 按钮生成本地预览；仅“采用到开题草稿”调用 `adoptAiPreview` 修改编辑内容。真实性确认未勾选时提交按钮 disabled；提交时先保存当前草稿，再调用 `submitMaterialRevision`，成功后更新状态并显示提交时间。
- 所有异步操作使用 `ElMessage` 和 `loading` 状态；API 失败显示“保存失败，请检查登录状态或稍后重试”，不更新本地成功状态。

- [ ] **Step 4: 执行前端完整验证。**

Run: `cd frontend && npm test && npm run build`  
Expected: 所有 Vitest 测试通过，Vite 构建成功。

### Task 4: 联调与回归

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-12-student-project-flow-design.md`

- [ ] **Step 1: 增加后端回归测试，确保非指定教师不能审批。**

```python
def test_only_selected_teacher_or_school_admin_can_approve_proposal(self):
    proposal = Proposal.objects.create(school=school, applicant=student, teacher=selected_teacher, title='题目', problem='问题')
    client.force_authenticate(other_teacher)
    self.assertEqual(client.post(f'/api/proposals/{proposal.id}/approve/').status_code, 403)
```

- [ ] **Step 2: 运行测试确认权限行为。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test apps.core.tests -v 2`  
Expected: 通过；非指定教师返回 403。

- [ ] **Step 3: 更新 README 与设计实现状态。**

README 写明学生需要先通过 `/api/me/` 识别身份；学生端依赖后端登录会话；开题内容须由学生确认真实性后才能提交。设计规格标注已实现接口及仍未接入的真实 AI/教师审批界面。

- [ ] **Step 4: 执行全量验证。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test && /opt/anaconda3/bin/python3.12 manage.py check && cd ../frontend && npm test && npm run build`  
Expected: Django 测试/系统检查、前端测试/构建全部通过。
