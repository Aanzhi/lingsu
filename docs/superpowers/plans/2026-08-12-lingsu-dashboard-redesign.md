# 灵溯工作台改版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将科创工坊改为极简北欧风的灵溯，并实现角色化工作台、赛事和公告。

**Architecture:** Django 新增学校隔离的赛事、公告与公告已读资源，通过现有 DRF Router 暴露 API。Vue 用单一 App Shell 承载顶部导航、AI 首屏和角色工作台；本地演示角色由页面状态选择，真实登录接入后以 `/me` 的 `role` 替代。

**Tech Stack:** Vue 3、TypeScript、Element Plus、Vitest；Django、Django REST Framework、Django TestCase。

---

### Task 1: 赛事与公告后端资源

**Files:**
- Modify: `backend/apps/core/models.py`
- Modify: `backend/apps/core/serializers.py`
- Modify: `backend/apps/core/views.py`
- Modify: `backend/apps/core/urls.py`
- Create: `backend/apps/core/migrations/0002_competition_announcement.py`
- Modify: `backend/apps/core/tests/test_workflows.py`

- [ ] **Step 1: 写入失败测试，验证学生只能读取自己学校已发布且面向学生的赛事/公告。**

```python
def test_student_sees_only_published_school_competitions_and_audience_announcements(self):
    school = School.objects.create(name="星辰学校")
    other = School.objects.create(name="其他学校")
    student = Account.objects.create_user(username="s", school=school, role="student")
    Competition.objects.create(school=school, title="校内赛", status="published")
    Competition.objects.create(school=other, title="外校赛", status="published")
    Announcement.objects.create(school=school, title="学生通知", audience="students", status="published", author=student)
    client = APIClient(); client.force_authenticate(student)
    self.assertEqual([x["title"] for x in client.get("/api/competitions/").data], ["校内赛"])
    self.assertEqual([x["title"] for x in client.get("/api/announcements/").data], ["学生通知"])
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test apps.core.tests -v 2`  
Expected: FAIL，提示 `Competition` 或 API 路由不存在。

- [ ] **Step 3: 实现赛事、公告和已读记录模型及序列化接口。**

```python
class Competition(SchoolBound):
    class Status(models.TextChoices): DRAFT = "draft", "草稿"; PUBLISHED = "published", "已发布"
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    registration_deadline = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    audience = models.CharField(max_length=16, default="all")
    template = models.ForeignKey(Template, null=True, blank=True, on_delete=models.SET_NULL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)

class Announcement(SchoolBound):
    title = models.CharField(max_length=160)
    body = models.TextField()
    audience = models.CharField(max_length=16, default="all")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, default="draft")
    published_at = models.DateTimeField(null=True, blank=True)

class AnnouncementRead(models.Model):
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    read_at = models.DateTimeField(auto_now_add=True)
```

实现 `CompetitionViewSet` 与 `AnnouncementViewSet`：查询同时按学校、`published` 状态和 `audience in (all, students/teachers)` 过滤；学校管理员/超级管理员可读写全校资源，教师仅能创建 `students` 受众公告。公告 detail action `mark_read` 使用 `get_or_create` 建立已读记录。

- [ ] **Step 4: 生成迁移并运行后端测试。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py makemigrations core && /opt/anaconda3/bin/python3.12 manage.py test && /opt/anaconda3/bin/python3.12 manage.py check`  
Expected: 迁移包含 Competition、Announcement、AnnouncementRead；全部测试通过且 check 无错误。

### Task 2: 角色化工作台状态与测试

**Files:**
- Modify: `frontend/src/stores/project.ts`
- Modify: `frontend/src/stores/project.test.ts`
- Create: `frontend/src/stores/dashboard.ts`
- Create: `frontend/src/stores/dashboard.test.ts`

- [ ] **Step 1: 写入失败测试，定义角色工作台内容与导航可见性。**

```ts
import { describe, expect, it } from 'vitest'
import { dashboardForRole, visibleNavigation } from './dashboard'

describe('role dashboard', () => {
  it('gives a teacher the review assistant and review work', () => {
    expect(dashboardForRole('teacher').aiTitle).toContain('审核')
    expect(dashboardForRole('teacher').primaryPanel).toBe('待审核材料')
  })
  it('hides school management for students', () => {
    expect(visibleNavigation('student')).not.toContain('学校管理')
  })
})
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `cd frontend && npm test -- dashboard.test.ts`  
Expected: FAIL，提示找不到 `./dashboard`。

- [ ] **Step 3: 实现角色工作台的纯函数。**

```ts
export type UserRole = 'student' | 'teacher' | 'school_admin'
export const visibleNavigation = (role: UserRole) =>
  role === 'school_admin'
    ? ['工作台', '项目', 'AI 助手', '案例库', '赛事', '公告', '学校管理']
    : ['工作台', '项目', 'AI 助手', '案例库', '赛事', '公告']
export const dashboardForRole = (role: UserRole) => ({
  aiTitle: role === 'student' ? '灵溯 AI · 项目教练' : role === 'teacher' ? '灵溯 AI · 审核助手' : '灵溯 AI · 管理助手',
  primaryPanel: role === 'student' ? '当前项目' : role === 'teacher' ? '待审核材料' : '学校运营',
})
```

- [ ] **Step 4: 运行前端单元测试。**

Run: `cd frontend && npm test`  
Expected: 所有材料状态与角色工作台测试通过。

### Task 3: 灵溯统一壳层与极简北欧视觉

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/api.ts`

- [ ] **Step 1: 写入工作台状态测试，覆盖教师审核抽屉与学生 AI 快捷动作。**

```ts
it('opens the review detail when a teacher selects a submitted item', () => {
  expect(nextDrawer('teacher', 'review')).toBe('review')
})
it('uses project coach actions for a student', () => {
  expect(dashboardForRole('student').aiActions).toContain('模拟答辩')
})
```

- [ ] **Step 2: 运行测试确认失败。**

Run: `cd frontend && npm test -- dashboard.test.ts`  
Expected: FAIL，提示 `nextDrawer` 或 `aiActions` 未定义。

- [ ] **Step 3: 扩充状态模块并重写 App Shell。**

实现 `nextDrawer(role, action)` 纯函数和每角色四项 `aiActions`；重写 `App.vue`：

```vue
<header class="topbar">
  <a class="brand">◌ 灵溯</a>
  <nav><button v-for="item in navigation" :class="{ active: activePage === item }">{{ item }}</button></nav>
  <div class="identity">{{ roleLabel }}</div>
</header>
<main class="workspace">
  <section class="ai-hero">...</section>
  <section class="dashboard-grid">...</section>
  <el-drawer v-model="drawerOpen">...</el-drawer>
</main>
```

视觉规则：移除 `.aside` 和深蓝渐变；根背景设为 `#f7f6f2`，主色 `#52765b`，AI 面板 `#e5eee4`，卡片白色、边框 `#d6ddd4`；顶部固定为白底单行导航。页面使用 `role` 演示选择器（仅开发环境显示），正常行为读取未来 `/api/me/` 的 `role`。赛事和公告放进主工作台右栏，并提供对应详情抽屉。

- [ ] **Step 4: 接入赛事与公告 API 适配函数。**

```ts
export const getCompetitions = () => api.get('/competitions/')
export const getAnnouncements = () => api.get('/announcements/')
export const markAnnouncementRead = (id: number) => api.post(`/announcements/${id}/mark_read/`)
```

API 不可用时显示静态演示数据和“演示数据”提示，避免开发预览空白。

- [ ] **Step 5: 运行前端完整验证。**

Run: `cd frontend && npm test && npm run build`  
Expected: Vitest 通过；Vite 打包成功。

### Task 4: 后端权限回归与文档更新

**Files:**
- Modify: `backend/apps/core/tests/test_workflows.py`
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-08-12-lingsu-dashboard-redesign-design.md`

- [ ] **Step 1: 增加教师公告与学校赛事权限失败测试。**

```python
def test_teacher_cannot_publish_schoolwide_competition(self):
    client.force_authenticate(teacher)
    response = client.post('/api/competitions/', {'title': '校赛', 'status': 'published'}, format='json')
    self.assertEqual(response.status_code, 403)
```

- [ ] **Step 2: 运行测试确认失败或暴露权限缺口。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test apps.core.tests -v 2`  
Expected: FAIL，直到 `perform_create` 仅允许学校管理员/超级管理员创建赛事。

- [ ] **Step 3: 收紧 ViewSet 创建权限并补充 README。**

```python
def perform_create(self, serializer):
    if self.request.user.role not in ('school_admin', 'super_admin'):
        raise PermissionDenied('仅学校管理员可发布赛事。')
    serializer.save(school=self.request.user.school)
```

README 增加“灵溯角色入口”和赛事/公告 API 简述；设计文档补充已实现状态。

- [ ] **Step 4: 执行全量验证。**

Run: `cd backend && /opt/anaconda3/bin/python3.12 manage.py test && /opt/anaconda3/bin/python3.12 manage.py check && cd ../frontend && npm test && npm run build`  
Expected: Django 全部测试通过、系统检查通过、前端测试与构建通过。
