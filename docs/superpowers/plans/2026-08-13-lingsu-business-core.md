# 灵溯业务核心完善实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让学生项目、教师指导、团队协作、材料审核、公开案例和平台治理遵循一套不可绕过、可追溯、可由三端正确呈现的业务状态机。

**Architecture:** 保留 Django + DRF 的单体业务边界；把状态校验和状态变更从 `views.py` 抽到按领域划分的工作流服务中。Vue 不再自行推断业务结果，只显示 API 返回的项目、任务、材料与审核状态，并在无权操作时明确说明原因。

**Tech Stack:** Django 5、Django REST Framework、PostgreSQL、Celery、Vue 3、TypeScript、Pinia、Vitest、Docker Compose。

**运行约束：** 当前工作区不是 Git 仓库，不能执行计划模板中的 Git 提交步骤。每项完成后改用“测试结果 + 文档勾选 + `git diff` 不可用说明”作为检查点；不初始化新仓库、不覆盖现有用户文件。

---

## 0. 业务规则基线

下列规则是本计划的唯一业务依据。任何页面文案、API 或异步任务都不得绕过它们。

1. 项目状态只能是 `unclaimed → active → completed`。学生创建项目后进入本校项目池；只有本校教师可认领；只有所有必填任务完成后系统自动标为完成。
2. 团队成员只在项目已启动后可被邀请。流程固定为负责人邀请 → 被邀请学生接受/拒绝 → 主指导教师确认/拒绝；只有确认后成为正式成员。
3. 正式材料的协作模型是“成员可创建自己的草稿，负责人负责真实性确认与正式提交”。任何成员都不能提交别人的非本项目材料；项目负责人可提交成员的草稿，且提交后不能继续改写该版本。
4. 材料状态只能是 `draft → submitted → approved` 或 `draft → submitted → revision_required → submitted`。已通过材料不可直接新建替代版本；若未来要重开任务，必须新增教师显式“重开”动作，而不是隐式覆盖证据。
5. 任务状态只能从 `locked` 解锁为 `available`。提交时为 `pending_review`，打回时为 `revision_required`，该任务的所有必填材料均通过后为 `completed`。部分材料通过时任务仍是 `available`，不能显示“已通过”。
6. 只有项目主指导教师可审核待审核版本；打回必须有可执行意见。审核通过一次只影响该材料和相应任务，不能绕过锁定任务。
7. 学校停用或过期后，师生可以读取历史数据，但不能创建、认领、邀请、接受、提交、审核、导出或申请公开；平台管理员仍能恢复授权与下架公开案例。
8. 公开案例只能由项目负责人在项目完成后申请，必须至少选择一份已通过材料；教师驳回后负责人可修改同一申请并重新提交。对外只返回选择材料的摘要，绝不返回其他过程材料、附件或源码。
9. 所有影响项目进程的成功动作都写入非敏感审计事件：认领、成员决定、材料提交、审核、公开申请/处理、学校授权变更。密码、密钥和附件正文绝不写入审计事件。

## 1. 文件边界

| 文件 | 责任 |
| --- | --- |
| `backend/apps/core/workflows/project.py` | 项目认领、模板快照和任务/材料实例化。 |
| `backend/apps/core/workflows/material.py` | 材料草稿、负责人提交、教师审核、任务推进与成长值。 |
| `backend/apps/core/workflows/membership.py` | 邀请、学生回应、教师决定。 |
| `backend/apps/core/workflows/cases.py` | 公开申请、教师审核、负责人重新提交、平台可见性。 |
| `backend/apps/core/workflows/audit.py` | 审计事件构造，不记录敏感正文。 |
| `backend/apps/core/views.py` | 只保留 HTTP 输入、权限入口、序列化和对工作流的调用；后续任务按领域拆分。 |
| `backend/apps/core/models.py` | 状态枚举、审计对象字段和模型约束。 |
| `backend/apps/core/tests/test_business_rules.py` | 从状态机规则派生的接口回归测试。 |
| `frontend/src/stores/student.ts` | 使用服务端状态刷新材料与任务，不本地伪造通过/解锁。 |
| `frontend/src/pages/student/StudentTask.vue` | 区分“成员草稿”和“负责人正式提交”；不可操作时显示原因。 |
| `frontend/src/pages/student/PublicCaseApplication.vue` | 显示驳回意见、允许修改并重新提交。 |
| `frontend/src/api.ts` | 补充公开申请重提等明确的 API 函数及类型。 |

## 2. 任务 1：为核心状态机建立失败测试

**Files:**
- Create: `backend/apps/core/tests/test_business_rules.py`
- Modify: `backend/apps/core/tests/test_platform_flow.py`

- [x] **Step 1: 写出正式提交权限失败测试**

```python
def test_member_can_create_draft_but_only_leader_can_submit_it(self):
    revision = self.client_for(self.member).post(
        "/api/material-revisions/",
        {"material": self.material.id, "content": "组员的观察记录"},
        format="json",
    )
    denied = self.client_for(self.member).post(
        f"/api/material-revisions/{revision.data['id']}/submit/",
        {"truth_confirmed": True}, format="json",
    )
    accepted = self.client_for(self.leader).post(
        f"/api/material-revisions/{revision.data['id']}/submit/",
        {"truth_confirmed": True}, format="json",
    )
    self.assertEqual(denied.status_code, 403)
    self.assertEqual(accepted.status_code, 200)
```

- [x] **Step 2: 写出材料和任务不可逆边界失败测试**

```python
def test_approved_material_cannot_create_an_implicit_replacement_revision(self):
    self.material.status = "approved"
    self.material.save(update_fields=["status"])
    response = self.client_for(self.leader).post(
        "/api/material-revisions/",
        {"material": self.material.id, "content": "试图修改已通过证据"},
        format="json",
    )
    self.assertEqual(response.status_code, 400)

def test_task_stays_available_until_every_required_material_is_approved(self):
    second = Material.objects.create(project=self.project, task=self.task, title="第二份证据", required=True)
    revision = self.submitted_revision(self.material)
    response = self.client_for(self.teacher).post(
        f"/api/material-revisions/{revision.id}/review/",
        {"outcome": "approved", "comment": "通过"}, format="json",
    )
    self.assertEqual(response.status_code, 200)
    self.task.refresh_from_db()
    self.assertEqual(self.task.status, ProjectTask.Status.AVAILABLE)
    self.assertEqual(second.status, "draft")
```

- [x] **Step 3: 写出团队和公开申请边界失败测试**

```python
def test_leader_cannot_invite_members_before_teacher_claims_project(self):
    response = self.client_for(self.leader).post(
        "/api/member-invitations/",
        {"project": self.unclaimed_project.id, "invitee": self.member.id}, format="json",
    )
    self.assertEqual(response.status_code, 400)

def test_rejected_completed_project_case_can_be_resubmitted(self):
    case = self.rejected_case_for_completed_project()
    response = self.client_for(self.leader).post(
        f"/api/public-case-requests/{case.id}/resubmit/",
        {"public_summary": "已去除个人信息的公开摘要", "selected_materials": [self.public_material.id]},
        format="json",
    )
    self.assertEqual(response.status_code, 200)
    self.assertEqual(response.data["status"], "pending_teacher")
    self.assertEqual(response.data["review_comment"], "")
```

- [x] **Step 4: 运行测试确认红灯**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_business_rules -v 1
```

Expected: 失败原因必须是“非负责人也可提交”“已通过材料可新增版本”“未认领项目可邀请”或“重提路由不存在”，而不是导入或测试语法错误。

- [x] **Step 5: 检查点**

记录失败输出到本计划的实施记录，不修改既有业务代码。

## 3. 任务 2：抽出材料状态机并修正提交/审核逻辑

**Files:**
- Create: `backend/apps/core/workflows/__init__.py`
- Create: `backend/apps/core/workflows/material.py`
- Modify: `backend/apps/core/models.py`
- Modify: `backend/apps/core/views.py:426-545`
- Modify: `backend/apps/core/tests/test_business_rules.py`

- [x] **Step 1: 在模型中声明材料状态枚举**

```python
class Material(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "草稿"
        SUBMITTED = "submitted", "待审核"
        REVISION_REQUIRED = "revision_required", "需修订"
        APPROVED = "approved", "已通过"

    status = models.CharField(max_length=24, choices=Status.choices, default=Status.DRAFT)
```

为 `MaterialRevision` 声明相同的状态值，不更改数据库中已有字符串值；生成迁移只改变 choices 元数据。

- [x] **Step 2: 在工作流中写入唯一状态判断**

```python
EDITABLE_MATERIAL_STATUSES = {Material.Status.DRAFT, Material.Status.REVISION_REQUIRED}
ACTIONABLE_TASK_STATUSES = {ProjectTask.Status.AVAILABLE, ProjectTask.Status.REVISION_REQUIRED}

def validate_material_draft(*, material, actor):
    project = material.project
    if project.status != Project.Status.ACTIVE or not project.primary_teacher_id:
        raise ValidationError("项目尚未由教师认领并启动，不能创建正式材料版本。")
    if not project_member(project, actor):
        raise PermissionDenied("无项目权限。")
    if material.status not in EDITABLE_MATERIAL_STATUSES:
        raise ValidationError("该材料当前不可新建版本；请等待审核结果或由教师重开任务。")
    if material.task_id and material.task.status not in ACTIONABLE_TASK_STATUSES:
        raise ValidationError("任务当前不可编辑，请先完成前置条件或等待审核结果。")

def submit_revision(*, revision, actor):
    if revision.material.project.leader_id != actor.id:
        raise PermissionDenied("仅项目负责人可确认真实性并正式提交材料。")
    # 校验 revision 草稿、正文/附件、扫描状态；随后原子更新 revision/material/task。
```

`review_revision()` 仅接受 `submitted` 版本；通过后把材料设为 `approved`。如果仍有必填材料未通过，将任务设为 `available`；全部通过时将任务设为 `completed` 并只解锁紧邻的锁定任务。

- [x] **Step 3: 让视图只调用工作流**

```python
def perform_create(self, serializer):
    require_authorized_school(self.request.user)
    revision = create_material_draft(
        material=serializer.validated_data["material"],
        actor=self.request.user,
        serializer=serializer,
    )
    return revision

@action(detail=True, methods=["post"])
def submit(self, request, pk=None):
    revision = self.get_object()
    return Response(MaterialRevisionSerializer(
        submit_revision(revision=revision, actor=request.user, truth_confirmed=request.data.get("truth_confirmed")),
        context={"request": request},
    ).data)
```

保留现有附件扫描和异步任务逻辑；不得在视图或前端重复推导任务完成状态。

- [x] **Step 4: 运行状态机测试确认绿灯**

### 2026-08-13：平台诊断从“已配置”改为“真实可用”

- **现象**：平台服务状态页把 Redis、ClamAV 和 Gotenberg 的环境变量存在当成服务健康，容器实际不可达时仍会误导为正常。
- **根因**：`ServiceStatusView` 没有在不泄露配置的前提下执行依赖探测。
- **处理**：增加统一的只读探测函数；Redis `PING`、ClamAV `PING`、Gotenberg `GET /health` 都限制为 2 秒。未配置返回“未配置”，探测异常返回“不可用”。
- **验证**：平台状态接口测试覆盖三项依赖和脱敏输出；集成容器中三项真实探测均返回 `healthy`。

### 2026-08-13：报告导出请求未进入审计链

- **现象**：报告生成已经异步排队，但平台不能回溯“谁在何时为哪个项目请求了什么格式的导出”。
- **根因**：导出视图创建 `ReportExport` 后直接投递 Celery 任务，遗漏了审计事件。
- **处理**：新增 `report_export_requested` 枚举，并在创建导出记录的同一请求中保存项目 ID、导出 ID 与格式；不记录报告正文、附件或下载地址。
- **验证**：导出测试断言负责人、学校、对象 ID 和格式均正确；迁移仅改变 `AuditEvent.action` 的 choices 元数据。

### 2026-08-13：字符串布尔值会绕过关键状态确认

- **现象**：`bool("false")` 在 Python 中为真，导致平台案例可见性、教师成员审批和学生真实性确认在接收到字符串时可能执行错误动作。
- **根因**：三个 HTTP action 直接将请求参数传入 `bool()`，没有区分 JSON 布尔值与字符串。
- **处理**：案例可见性和成员审批仅接受真正的 JSON `true`/`false`；材料提交只接受 `true`，保留原有 `false` 的“须确认真实性”提示，字符串则返回字段错误。学校授权更新同步拒绝字符串布尔值。
- **验证**：新增案例、成员、材料和学校配置边界用例；后端全量 98 项测试通过。

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_business_rules apps.core.tests.test_workflows apps.core.tests.test_upload_policy -v 1
```

Expected: 新增状态机测试与既有上传/审核测试全部通过。

- [x] **Step 5: 生成并核对迁移**

Run:

```bash
docker compose --env-file .env.integration exec -T backend python manage.py makemigrations core
docker compose --env-file .env.integration exec -T backend python manage.py migrate --noinput
```

Expected: 只出现材料/版本状态 choices 的迁移，不删除、重置或重写现有项目数据。

## 4. 任务 3：收紧项目认领与团队协作状态机

**Files:**
- Create: `backend/apps/core/workflows/project.py`
- Create: `backend/apps/core/workflows/membership.py`
- Modify: `backend/apps/core/views.py:141-208`
- Modify: `backend/apps/core/views.py:713-764`
- Modify: `backend/apps/core/tests/test_business_rules.py`

- [x] **Step 1: 写出认领与邀请的竞争边界测试**

```python
def test_second_teacher_cannot_claim_project_after_first_teacher_claims_it(self):
    first = self.client_for(self.teacher).post(f"/api/projects/{self.unclaimed_project.id}/claim/")
    second = self.client_for(self.other_teacher).post(f"/api/projects/{self.unclaimed_project.id}/claim/")
    self.assertEqual(first.status_code, 200)
    self.assertEqual(second.status_code, 400)

def test_only_active_project_leader_can_create_member_invitation(self):
    response = self.client_for(self.member).post(
        "/api/member-invitations/",
        {"project": self.active_project.id, "invitee": self.another_student.id}, format="json",
    )
    self.assertEqual(response.status_code, 403)
```

- [x] **Step 2: 运行测试确认红灯或覆盖缺口**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_business_rules -v 1
```

Expected: 未认领邀请测试失败；已有认领竞争与负责人限制可保持通过。

- [x] **Step 3: 实现项目认领服务**

`claim_project()` 必须在事务内锁定项目、验证 `UNCLAIMED` 和 `primary_teacher is None`、验证模板属于同校且已发布、生成任务与材料快照，并在全部创建成功后将项目切换到 `ACTIVE`。不得在事务之外先改项目状态。

```python
@transaction.atomic
def claim_project(*, project, teacher, template_id=None):
    project = Project.objects.select_for_update().get(pk=project.pk)
    if project.status != Project.Status.UNCLAIMED or project.primary_teacher_id:
        raise ValidationError("该项目已被认领。")
    template = resolve_template(project=project, teacher=teacher, template_id=template_id)
    instantiate_template(project=project, template=template)
    project.primary_teacher = teacher
    project.status = Project.Status.ACTIVE
    project.save(update_fields=["primary_teacher", "status", "template_snapshot"])
    return project
```

- [x] **Step 4: 实现成员邀请服务**

`create_invitation()` 必须检查项目已启动且有主指导教师、邀请者是负责人、被邀请者是同校活跃学生且不是成员。`accept_invitation()`、`reject_invitation()` 和 `decide_invitation()` 分别仅接受对应前一状态；教师拒绝不能创建成员关系。

- [x] **Step 5: 运行协作回归**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_business_rules apps.core.tests.test_platform_flow apps.core.tests.test_production_contract -v 1
```

Expected: 项目池、认领、邀请、接受、教师确认和跨校限制全部通过。

## 5. 任务 4：完善公开案例的完成条件与重提闭环

**Files:**
- Create: `backend/apps/core/workflows/cases.py`
- Modify: `backend/apps/core/views.py:784-828`
- Modify: `backend/apps/core/serializers.py:135-159`
- Modify: `backend/apps/core/urls.py`
- Modify: `backend/apps/core/tests/test_public_cases.py`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/student/PublicCaseApplication.vue`

- [x] **Step 1: 写出失败的完成条件和重提测试**

```python
def test_unfinished_project_cannot_request_publication(self):
    response = self.client_for(self.leader).post(
        "/api/public-case-requests/", self.valid_payload(), format="json",
    )
    self.assertEqual(response.status_code, 400)
    self.assertIn("完成", str(response.data))

def test_only_leader_can_resubmit_rejected_case(self):
    case = self.rejected_completed_case()
    response = self.client_for(self.member).post(
        f"/api/public-case-requests/{case.id}/resubmit/", self.valid_payload(), format="json",
    )
    self.assertEqual(response.status_code, 403)
```

- [x] **Step 2: 运行测试确认红灯**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_public_cases -v 1
```

Expected: 未完成项目可以申请或 `resubmit` 不存在导致失败。

- [x] **Step 3: 在工作流服务中实施公开规则**

```python
def validate_public_case_payload(*, project, selected_materials):
    if project.status != Project.Status.COMPLETED:
        raise ValidationError("项目完成后才能申请公开案例。")
    if not selected_materials:
        raise ValidationError({"selected_materials": "至少选择一份已通过材料公开。"})
    invalid = [item.id for item in selected_materials if item.project_id != project.id or item.status != Material.Status.APPROVED]
    if invalid:
        raise ValidationError({"selected_materials": "只能选择本项目已通过的材料公开。"})
```

增加 `POST /api/public-case-requests/{id}/resubmit/`：仅申请人且项目负责人、仅 `rejected` 状态可调用；更新摘要、标签和材料白名单，清空审核意见/教师审核人，切回 `pending_teacher`。

- [x] **Step 4: 在学生页面消费重提 API**

页面对 `rejected` 申请显示教师意见、预填最后一次公开信息、主按钮显示“修改并重新提交”；`pending_teacher` 和 `published` 仅显示只读状态，不重复创建同一申请。

- [x] **Step 5: 验证后端和前端类型**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_public_cases -v 1
cd frontend && npm test -- --reporter=dot && npm run build
```

Expected: 案例接口测试通过；前端类型检查与构建通过。

## 6. 任务 5：审计事件覆盖核心状态变化

**Files:**
- Modify: `backend/apps/core/models.py`
- Create: `backend/apps/core/workflows/audit.py`
- Modify: `backend/apps/core/workflows/project.py`
- Modify: `backend/apps/core/workflows/material.py`
- Modify: `backend/apps/core/workflows/membership.py`
- Modify: `backend/apps/core/workflows/cases.py`
- Create: `backend/apps/core/tests/test_audit_events.py`
- Create: `backend/apps/core/migrations/00xx_expand_audit_event.py`

- [x] **Step 1: 写出非敏感审计失败测试**

```python
def test_material_review_audit_keeps_metadata_without_material_body(self):
    revision = self.submitted_revision()
    self.client_for(self.teacher).post(
        f"/api/material-revisions/{revision.id}/review/",
        {"outcome": "revision_required", "comment": "补充对照组"}, format="json",
    )
    event = AuditEvent.objects.get(action=AuditEvent.Action.MATERIAL_REVIEWED)
    self.assertEqual(event.actor_id, self.teacher.id)
    self.assertEqual(event.target_type, "material_revision")
    self.assertNotIn(revision.content, str(event.changes))
    self.assertNotIn("补充对照组", str(event.changes))
```

- [x] **Step 2: 扩展审计模型与统一记录函数**

```python
class AuditEvent(models.Model):
    class Action(models.TextChoices):
        PROJECT_CLAIMED = "project_claimed", "项目已认领"
        MATERIAL_SUBMITTED = "material_submitted", "材料已提交"
        MATERIAL_REVIEWED = "material_reviewed", "材料已审核"
        MEMBER_DECIDED = "member_decided", "成员邀请已处理"
        CASE_SUBMITTED = "case_submitted", "公开申请已提交"
        CASE_REVIEWED = "case_reviewed", "公开申请已审核"
        CASE_VISIBILITY_CHANGED = "case_visibility_changed", "案例可见性已变更"
        SCHOOL_UPDATED = "school_updated", "学校配置已更新"
        INVITE_CODE_RESET = "invite_code_reset", "邀请码已重置"

    target_type = models.CharField(max_length=40, blank=True)
    target_id = models.PositiveBigIntegerField(null=True, blank=True)
```

`record_audit_event()` 只接收标量 ID、状态和数量，不接收 `content`、`prompt`、`output`、`review_comment`、密码、密钥或文件路径。

- [x] **Step 3: 在成功状态变更后记录事件**

使用 `transaction.on_commit()` 或同一事务内创建事件，确保业务动作失败时不会留下成功审计记录。

- [x] **Step 4: 运行审计和全量核心测试**

Run:

```bash
docker compose --env-file .env.integration exec -T backend \
  python manage.py test apps.core.tests.test_audit_events apps.core.tests.test_business_rules apps.core.tests.test_platform_configuration -v 1
```

Expected: 审计条目记录正确、无正文泄漏，原学校配置审计不回归。

## 7. 任务 6：让前端准确呈现负责人/成员状态

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/pages/student/StudentTask.vue`
- Modify: `frontend/src/pages/student/StudentProject.vue`
- Modify: `frontend/src/pages/student/StudentInvitations.vue`
- Create: `frontend/src/stores/projectPermissions.ts`
- Create: `frontend/src/stores/projectPermissions.test.ts`

- [x] **Step 1: 为权限文案写失败测试**

```ts
it('lets a team member save evidence but reserves formal submission for the leader', () => {
  expect(taskPermission({ isLeader: false, taskStatus: 'available', materialStatus: 'draft' }))
    .toEqual({ canDraft: true, canSubmit: false, reason: '请由项目负责人确认真实性并正式提交。' })
})
```

- [x] **Step 2: 运行前端测试确认红灯**

Run:

```bash
cd frontend && npm test -- src/stores/projectPermissions.test.ts
```

Expected: 模块不存在导致失败。

- [x] **Step 3: 实现纯权限映射并接入任务页**

```ts
export function taskPermission(input: TaskPermissionInput) {
  if (!['available', 'revision_required'].includes(input.taskStatus)) {
    return { canDraft: false, canSubmit: false, reason: '当前任务不可编辑。' }
  }
  if (!['draft', 'revision_required'].includes(input.materialStatus)) {
    return { canDraft: false, canSubmit: false, reason: '材料正在审核或已通过。' }
  }
  return input.isLeader
    ? { canDraft: true, canSubmit: true, reason: '' }
    : { canDraft: true, canSubmit: false, reason: '请由项目负责人确认真实性并正式提交。' }
}
```

成员按钮使用“保存我的草稿”；负责人显示真实性确认和“正式提交审核”。提交 API 返回 403 时保留草稿和附件，显示 API 的可执行原因。

- [x] **Step 4: 运行前端聚焦验证**

Run:

```bash
cd frontend && npm test -- src/stores/projectPermissions.test.ts src/stores/studentApiModel.test.ts && npm run build
```

Expected: 权限映射、既有任务状态模型和生产构建通过。

## 8. 任务 7：后续生产化批次（不阻塞本业务规则计划）

本任务不在本计划中实现，但后续必须按顺序进入新的独立计划：

1. 将 `views.py` 按认证、项目、材料、内容、平台拆到多个小于 600 行的模块，并用 `urls.py` 聚合。
2. 将 `lingsu-system.css` 按设计令牌、布局、学生、教师、平台分拆；保持当前暖白北欧研究手帐风格。
3. 实现三条浏览器 E2E：登录/角色路由、提交—打回—重提—通过、授权只读。
4. 完成正式 HTTPS、Secure Cookie、HSTS、结构化日志、任务监控、备份恢复演练和上线手册。
5. 以数据库事务或配额预留修正 AI 并发扣减，并允许指导教师只读查看自己项目的 AI 审核摘要。

## 9. 计划自检

- 业务规则 1–9 分别由任务 2、3、4、5、6 覆盖。
- 所有状态变更都有失败测试、红灯、最小实现和绿灯命令。
- 未引入第二数据库、微服务、WebSocket 或额外身份系统。
- 计划中没有假定存在 Git；不执行可能覆盖用户数据的初始化、重置或清理操作。
- 文件按领域拆分，新增文件职责单一；本计划不让任何单一源码文件超过 600 行。

## 10. 实施记录与防复发

| 日期 | 现象 | 根因 | 解决方法 | 防复发措施 |
| --- | --- | --- | --- | --- |
| 2026-08-13 | 新增后端测试在运行容器中显示为不存在 | 集成 Compose 使用生产镜像源码，未挂载宿主机 `backend/` 目录 | 修改后先重建 `backend` 与 `celery` 镜像，再在容器运行测试 | 后端代码验证固定包含镜像重建步骤，不误判为 Python 导入错误。 |
| 2026-08-13 | 组员可绕过负责人直接正式提交，部分材料通过即显示任务完成 | 状态变更散落在 DRF 视图，缺少统一前置条件与完成判定 | 建立 `workflows/materials.py`，集中草稿、提交、审核、任务推进与成长记录 | 后续写操作只通过领域工作流；新增状态规则先以失败用例锁定。 |
| 2026-08-13 | 未认领项目可以组队，驳回案例无法重提 | 邀请和案例申请缺失项目状态/重提动作 | 限制邀请到已启动项目，新增 `resubmit` API 和案例完成条件 | 规则变化同步更新 API 测试和产品规则，杜绝过时测试覆盖新决策。 |
| 2026-08-13 | 旧案例测试仍允许进行中项目公开 | 测试描述落后于“项目完成后才可公开”的已确认规则 | 将正常公开用例改为完成项目，并新增进行中项目拒绝用例 | 审核需求变更时，一并检查测试的前置状态。 |
| 2026-08-13 | 从项目根目录执行 `npm run build` 失败 | Vite 脚本属于 `frontend/` 子项目，而非 Compose 根目录 | 改为 `cd frontend && npm run build` 后重跑 | 每条验证命令标明所属子项目工作目录，不把命令错误误判为构建故障。 |
| 2026-08-13 | 负责人无法从页面提交成员草稿 | 后端允许负责人提交任意项目成员的草稿，但页面只提供新建材料入口 | 任务页识别成员草稿，显示核对说明与“确认并提交成员草稿”动作 | 页面权限映射必须以服务端可执行的实际动作建模，而不是只按作者显示。 |
| 2026-08-13 | 指导教师在 AI 中心看不到学生的项目 AI 历史 | AI 查询固定按请求者 `actor` 过滤，和“教师可审核项目上下文”的产品规则冲突 | 以 `workflows/ai.py` 按角色筛选：学生仅自己，教师仅自己指导项目 | 查询权限测试至少覆盖学生本人、同校非成员、主指导教师三类主体。 |
| 2026-08-13 | AI 月度配额先计数再创建，存在并发超额风险 | 多个请求可同时读到同一个使用量，随后都创建记录 | 在同一事务中锁定学校行，再计数并创建 AI 记录 | 低频单校试点先使用现有学校行锁；高并发时再引入专门的配额预留记录。 |
