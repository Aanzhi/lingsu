# 灵溯试点可用化实施计划

> **执行说明：** 后续实施时按任务逐项使用测试驱动开发；每完成一个任务，都必须重新运行前端测试/构建、后端测试和对应浏览器链路，不以“页面能打开”作为完成标准。

**目标：** 把当前可运行的 Alpha 原型推进为可以交给一所学校进行受控试点的完整 MVP，确保学生、教师、平台管理员三条核心链路真实闭环，AI、材料、报告、通知和授权状态都有明确且可验证的结果。

**架构原则：** 保留 Vue 3 + Django REST + PostgreSQL + Celery 的现有边界。前端按角色布局与业务模块拆分，统一使用 Pinia 管理远端状态；后端继续以学校范围过滤和角色权限作为数据边界。所有异步能力都暴露“排队、处理中、成功、失败、重试”状态，所有重要写操作都具备确认、反馈与审计记录。

**技术栈：** Vue 3、TypeScript、Vue Router、Pinia、Element Plus、Vitest、Vue Test Utils、Playwright；Django 5、DRF、PostgreSQL、Celery、Redis、ClamAV、Gotenberg；Docker Compose、GitHub Actions。

---

## 阶段一：修复可信性与关键交互（P0，2–3 天）

### 任务 1：建立真正的浏览器端验收基线

**文件：**
- 修改：`frontend/package.json`
- 新建：`frontend/playwright.config.ts`
- 新建：`frontend/e2e/auth-routing.spec.ts`
- 新建：`frontend/e2e/student-teacher-loop.spec.ts`
- 新建：`frontend/e2e/platform-license.spec.ts`
- 新建：`.github/workflows/quality.yml`

**步骤：**
1. 先编写失败的路由、学生提交/教师打回/学生重提/教师通过、平台停用授权三条 E2E 测试。
2. 增加 Playwright 和 Vue Test Utils；在 CI 中启动测试数据库、Redis、Django、Celery 和 Vite。
3. 让 CI 依次执行前端单元测试、类型检查、生产构建、后端 78+ 测试和 E2E。
4. 验证刷新、浏览器前进后退、直接输入深层 URL、错误角色访问均符合预期。

**完成标准：** 不再依赖人工切换标签判断路由是否正常；三条主链路在干净数据库中可重复通过。

### 任务 2：清理“假交互”和全局反馈缺口

**文件：**
- 修改：`frontend/src/components/AppTopbar.vue`
- 修改：`frontend/src/components/ConfirmDialog.vue`
- 修改：`frontend/src/pages/shared/ContentLibrary.vue`
- 修改：`frontend/src/pages/student/StudentHome.vue`
- 修改：`frontend/src/pages/platform/PlatformConsole.vue`
- 修改：`frontend/src/lingsu-system.css`
- 新建：`frontend/src/components/FeedbackBanner.vue`
- 新建：`frontend/src/components/NotificationDrawer.vue`

**步骤：**
1. 为品牌入口、通知、帮助、搜索按钮编写组件测试，确认它们当前行为不完整。
2. 品牌可返回当前角色首页；通知抽屉读取公告并调用已存在的已读接口；帮助入口提供角色化指引。
3. 搜索按钮执行明确的检索动作，同时保留键盘回车；无结果、加载和失败有统一反馈。
4. 邀请码重置、学校停用、赛事下架、案例下架使用确认弹窗，成功/失败均可见。
5. 将学生“接取任务”改为“开始任务”，或者增加真实的任务接取状态；禁止文案与数据语义不一致。

**完成标准：** 页面上所有看起来可交互的元素都有结果；不存在装饰性按钮冒充功能入口。

### 任务 3：修正成长值和审计语义

**文件：**
- 修改：`backend/apps/core/models.py`
- 修改：`backend/apps/core/views.py`
- 修改：`backend/apps/core/serializers.py`
- 新建迁移：`backend/apps/core/migrations/000x_growth_and_audit.py`
- 新建：`backend/apps/core/tests/test_growth_semantics.py`
- 新建：`backend/apps/core/tests/test_audit_events.py`

**步骤：**
1. 先覆盖“同一天通过多份材料不能把连续天数累加多次”的失败测试。
2. 为成长记录增加最后有效活动日期，按自然日计算连续完成，不按审核次数累加。
3. 增加通用审计事件，记录教师认领、材料审核、成员确认、学校授权变更、邀请码重置和案例治理。
4. 审计事件只保存必要业务字段，不保存 AI 密钥、密码或附件正文。

**完成标准：** XP、等级、连续天数均能解释且可追溯；平台敏感操作有操作人和时间。

---

## 阶段二：补齐三端业务深度（P1，4–6 天）

### 任务 4：拆分前端模块并统一状态管理

**文件：**
- 重构：`frontend/src/pages/student/StudentProject.vue`
- 重构：`frontend/src/pages/teacher/TeacherWorkbench.vue`
- 重构：`frontend/src/pages/platform/PlatformConsole.vue`
- 重构：`frontend/src/stores/student.ts`
- 重构：`frontend/src/stores/teacher.ts`
- 重构：`frontend/src/stores/platform.ts`
- 新建：`frontend/src/pages/teacher/TeacherProjectDetail.vue`
- 新建：`frontend/src/pages/platform/SchoolDetail.vue`
- 新建：`frontend/src/stores/modules/*.ts`

**步骤：**
1. 为每个页面的数据加载、空状态、失败、写入和刷新编写 store/组件测试。
2. 使用 Pinia `defineStore` 替换当前模块级 reactive 单例，按项目、审核、内容、授权拆分状态。
3. 将依赖 `route.meta.surface` 的大型组件拆成独立页面组件，保留共享的领域组件。
4. 统一请求取消、重复提交保护、错误映射和成功反馈。

**完成标准：** 每条路由对应明确页面职责；页面内部不再通过大量条件分支模拟多个页面；状态可独立测试和重置。

### 任务 5：完成教师指导项目工作台

**文件：**
- 新建：`frontend/src/pages/teacher/TeacherProjectDetail.vue`
- 新建：`frontend/src/components/teacher/ProjectRiskPanel.vue`
- 新建：`frontend/src/components/teacher/TeamManager.vue`
- 修改：`backend/apps/core/serializers.py`
- 修改：`backend/apps/core/views.py`
- 新建：`backend/apps/core/tests/test_teacher_project_detail.py`

**步骤：**
1. 增加教师项目详情接口测试：阶段、任务、材料状态、成员、逾期和待修订风险必须一次可读。
2. 教师详情页显示任务地图、材料通过率、成员邀请、最近活动和风险项，而不是重复项目列表卡片。
3. 教师可设置任务截止时间、查看版本差异、确认成员，并从项目详情进入待审核材料。
4. 认领项目后给学生明确反馈，并保证同一项目不能被重复认领。

**完成标准：** 教师能在一个项目详情页回答“谁在做、做到哪一步、卡在哪里、我下一步要处理什么”。

### 任务 6：完成平台授权和配置控制台

**文件：**
- 新建：`frontend/src/pages/platform/SchoolDetail.vue`
- 新建：`frontend/src/pages/platform/PlatformSettings.vue`
- 修改：`frontend/src/stores/platform.ts`
- 修改：`backend/apps/core/serializers.py`
- 修改：`backend/apps/core/views.py`
- 新建：`backend/apps/core/tests/test_platform_configuration.py`

**步骤：**
1. 先覆盖修改授权到期日、AI 配额、存储配额、授权启停和服务状态读取测试。
2. 学校详情提供可编辑表单、确认和审计记录，不再只显示配额数字。
3. 平台设置展示真实的 AI、Redis/Celery、ClamAV、Gotenberg 和存储健康状态；敏感密钥只显示是否配置。
4. 学校被停用或过期时，师生历史读取正常，所有受限写动作返回统一错误码和文案。

**完成标准：** 平台管理员可以独立完成开校、授权、配额调整、停用和服务诊断。

---

## 阶段三：AI、材料和成果输出（P1/P2，5–8 天）

### 任务 7：让 AI 成为可运营能力而非占位入口

**文件：**
- 修改：`backend/apps/core/tasks.py`
- 修改：`backend/apps/core/views.py`
- 修改：`backend/apps/core/serializers.py`
- 修改：`frontend/src/pages/shared/AICenter.vue`
- 修改：`frontend/src/stores/aiModel.ts`
- 新建：`backend/apps/core/tests/test_ai_context_and_quota.py`

**步骤：**
1. 增加 AI 服务可用性、上下文范围、配额并发和失败重试测试。
2. 上下文扩展到当前任务、教师反馈、最新可解析材料摘要和项目日志，同时明确来源范围。
3. 前端在输入前展示服务可用状态和剩余配额；未配置时禁用生成并给出平台处理路径。
4. 生成结果必须“预览 → 明确采用 → 写入草稿”，记录模型、时间、用途和资料范围。
5. 配额扣减使用数据库事务或预留机制，避免并发超额。

**完成标准：** AI 可用、不可用、超额、失败和成功都有可预测结果；教师可追溯学生采用过的内容。

### 任务 8：提升材料、报告与公开案例完整度

**文件：**
- 修改：`frontend/src/pages/student/StudentTask.vue`
- 修改：`frontend/src/pages/student/StudentProject.vue`
- 修改：`frontend/src/components/PublicCaseDialog.vue`
- 修改：`backend/apps/core/tasks.py`
- 修改：`backend/apps/core/models.py`
- 修改：`backend/apps/core/serializers.py`
- 新建：`backend/apps/core/tests/test_document_parsing.py`
- 新建：`backend/apps/core/tests/test_public_case_payload.py`

**步骤：**
1. 先覆盖文件进度、失败重试、解析状态、报告章节和公开材料白名单测试。
2. 文本编辑升级为可控富文本；上传显示逐文件进度、扫描/解析状态、取消与重试。
3. 增加文档文本/表格解析和图片 OCR 的异步任务；低置信度必须提示学生校对。
4. 报告支持封面、目录、图片、表格、引用和学校/赛事模板；失败任务可一键重试。
5. 公开申请支持封面和精选媒体，案例详情只读取白名单内容，并提供真正的详情页。

**完成标准：** 学生提交的主要材料可以被审阅、引用和装配；公开案例不会意外暴露过程附件或个人信息。

---

## 阶段四：试点上线保障（P2，3–5 天）

### 任务 9：可访问性、性能、安全与运维验收

**文件：**
- 修改：`frontend/src/lingsu-system.css`
- 修改：`frontend/src/components/*.vue`
- 修改：`docker-compose.yml`
- 修改：`README.md`
- 新建：`docs/runbooks/pilot-operations.md`
- 新建：`docs/runbooks/backup-restore.md`
- 新建：`frontend/e2e/accessibility.spec.ts`

**步骤：**
1. 增加 axe 扫描和 1280/1440 视觉回归；窄屏重要内容必须重排，不能直接隐藏证据要求。
2. 为图标按钮、复制按钮、弹窗焦点、表单错误和表格语义补齐无障碍属性。
3. 增加依赖审计、静态检查、格式化、日志和错误监控；建立 Git 仓库和保护分支。
4. 在预发布环境执行真实 500MB 上传、病毒扫描、Celery 失败恢复、PDF 导出和跨校越权测试。
5. 自动化每日备份，完成一次隔离恢复演练，记录 RPO/RTO 和联系人。
6. 用学生、教师、平台三个测试账号完成整套 UAT 并签署验收清单。

**完成标准：** 核心链路 E2E 全绿、无 P0/P1 缺陷、备份可恢复、跨校数据隔离通过、试点操作手册可执行。

---

## 推荐执行顺序与里程碑

1. **M1：可信闭环（第 1 周）** — 完成任务 1–3，消除假交互和数据语义错误。
2. **M2：三端完整（第 2 周）** — 完成任务 4–6，教师与平台端达到独立可用。
3. **M3：成果生产（第 3 周）** — 完成任务 7–8，AI、材料、报告和案例形成真实价值链。
4. **M4：一校试点（第 4 周）** — 完成任务 9，在预发布环境通过全链路 UAT。

每个里程碑的统一验收命令：

```bash
cd frontend && npm test && npm run build
cd backend && python manage.py test && python manage.py check && python manage.py makemigrations --check --dry-run
docker compose ps
```

此外，M1 起必须执行 Playwright E2E；M4 必须执行恢复演练与跨校权限专项测试。
