import { expect, test, type Page } from '@playwright/test'
import { login, seedCoreFlow } from './realAuth'

test.beforeAll(seedCoreFlow)

async function findProjectWithTasks(page: Page) {
  return page.evaluate(async () => {
    const projects = await (await fetch('/api/projects/', { credentials: 'include' })).json() as Array<{ id: number }>
    for (const project of projects) {
      const tasks = await (await fetch(`/api/project-tasks/?project=${project.id}`, { credentials: 'include' })).json() as Array<{ id: number }>
      if (Array.isArray(tasks) && tasks.length) return { id: project.id, taskCount: tasks.length, taskId: tasks[0].id }
    }
    return null
  })
}

async function findFirstId(page: Page, endpoint: string) {
  return page.evaluate(async (url) => {
    const response = await fetch(url, { credentials: 'include' })
    if (!response.ok) return null
    const data = await response.json() as Array<{ id: number }>
    return Array.isArray(data) && data.length ? data[0].id : null
  }, endpoint)
}

async function assertProductionRoute(page: Page, path: string) {
  await page.goto(path)
  await expect(page).not.toHaveURL(/\/login/)
  const content = page.locator('main .page, main .conversation-page').first()
  await expect(content, `production route did not render: ${path} (actual ${page.url()})`).toBeVisible()
  await expect.poll(async () => (await content.innerText()).trim().length, { message: `production route rendered no content: ${path}` }).toBeGreaterThan(8)
}

test('未登录用户先看到品牌入口', async ({ page }) => {
  await page.context().clearCookies()
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '把科创项目推进到结果。' })).toBeVisible()
  await expect(page.getByRole('link', { name: '登录工作台', exact: true })).toHaveCount(1)
  await expect(page.getByRole('link', { name: '登录', exact: true })).toHaveCount(0)
  await page.getByRole('link', { name: '注册学生账号', exact: true }).click()
  await expect(page).toHaveURL(/\/register\?role=student$/)
  await expect(page.getByRole('button', { name: /以学生身份注册/ })).toHaveAttribute('aria-pressed', 'true')
  await page.goto('/')
  await page.getByRole('link', { name: '登录教师工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)

  await page.goto('/')
  await page.getByRole('link', { name: '登录工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/login$/)
  await page.goto('/register')
  const studentRole = page.locator('button.auth-role-card--student')
  const teacherRole = page.locator('button.auth-role-card--teacher')
  await expect(studentRole).toHaveAttribute('aria-pressed', 'true')
  await teacherRole.click()
  await expect(teacherRole).toHaveAttribute('aria-pressed', 'true')
  await expect(studentRole).toHaveAttribute('aria-pressed', 'false')
})

test('Demo 对应的生产页面都能通过真实路由访问', async ({ page }) => {
  const surfaces = [
    ['student', '/student/home', '继续当前研究'],
    ['student', '/student/projects', '我的项目'],
    ['student', '/student/ai', '灵思 AI'],
    ['teacher', '/teacher/home', '指导工作台'],
    ['teacher', '/teacher/projects', '指导项目'],
    ['teacher', '/teacher/reviews', '学生材料审核'],
    ['platform_admin', '/platform/home', '平台概览'],
    ['platform_admin', '/platform/schools', '学校空间'],
    ['platform_admin', '/platform/ai-agents', 'AI 助手模板'],
  ] as const

  for (const [role, path, text] of surfaces) {
    await page.context().clearCookies()
    await login(page, role, path)
    await expect(page.getByText(text, { exact: false }).first()).toBeVisible()
  }
})

test('所有生产角色路由都有可达页面与明确入口', async ({ page }) => {
  test.setTimeout(90_000)

  await login(page, 'student', '/student/home')
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(1)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(0)
  await expect(page.locator('nav.student-top-navigation')).toHaveCount(0)
  await expect(page.getByRole('link', { name: '进入工作台', exact: true })).toBeVisible()
  await page.goto('/student/projects')
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(0)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
  await expect(page.getByRole('link', { name: '我的项目', exact: true })).toBeVisible()
  const studentProject = await findProjectWithTasks(page)
  const studentRoutes = [
    '/student/home', '/student/projects', '/student/ai', '/student/cases',
    '/student/competitions', '/student/announcements', '/student/invitations',
    '/student/notifications',
  ]
  for (const path of studentRoutes) await assertProductionRoute(page, path)
  if (studentProject) {
    for (const path of [
      `/student/projects/${studentProject.id}`,
      `/student/projects/${studentProject.id}/map`,
      `/student/projects/${studentProject.id}/materials`,
      `/student/projects/${studentProject.id}/report`,
      `/student/projects/${studentProject.id}/tasks/${studentProject.taskId}`,
      `/student/public-applications?projectId=${studentProject.id}`,
    ]) await assertProductionRoute(page, path)
  }

  await page.context().clearCookies()
  await login(page, 'teacher', '/teacher/home')
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(1)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(0)
  await expect(page.getByRole('link', { name: '进入工作台', exact: true })).toBeVisible()
  await page.goto('/teacher/projects')
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(0)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
  await expect(page.getByRole('link', { name: '内容资源', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '案例库', exact: true })).toHaveCount(0)
  await expect(page.getByRole('link', { name: '赛事信息', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '学生公告', exact: true })).toBeVisible()
  const teacherProject = await findProjectWithTasks(page)
  const teacherRoutes = [
    '/teacher/home', '/teacher/pool', '/teacher/projects', '/teacher/reviews',
    '/teacher/members', '/teacher/ai', '/teacher/cases', '/teacher/competitions', '/teacher/announcements',
    '/teacher/notifications',
  ]
  for (const path of teacherRoutes) await assertProductionRoute(page, path)
  if (teacherProject) {
    await assertProductionRoute(page, `/teacher/projects/${teacherProject.id}`)
    await assertProductionRoute(page, `/teacher/projects/${teacherProject.id}/template`)
  }
  const reviewId = await findFirstId(page, '/api/material-revisions/pending_reviews/')
  if (reviewId) await assertProductionRoute(page, `/teacher/reviews/${reviewId}`)

  await page.context().clearCookies()
  await login(page, 'platform_admin', '/platform/home')
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
  await expect(page.getByRole('link', { name: '赛事与公告', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '案例治理', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '系统公告', exact: true })).toBeVisible()
  const schoolId = await findFirstId(page, '/api/schools/')
  const platformRoutes = [
    '/platform/home', '/platform/schools', '/platform/competitions',
    '/platform/announcements', '/platform/cases', '/platform/settings', '/platform/ai-agents',
  ]
  for (const path of platformRoutes) await assertProductionRoute(page, path)
  await page.goto('/platform/licenses')
  await expect(page).toHaveURL(/\/platform\/schools$/)
  if (schoolId) await assertProductionRoute(page, `/platform/schools/${schoolId}`)
})

test('学生端首页使用 Hero 壳层，子页面切换到侧栏且不产生运行时错误', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('console', (message) => { if (message.type() === 'error') errors.push(message.text()) })
  await login(page, 'student', '/student/home')
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(1)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(0)
  await expect(page.locator('nav.student-top-navigation')).toHaveCount(0)
  await page.getByRole('link', { name: '进入工作台', exact: true }).click()
  await expect(page).toHaveURL(/\/student\/projects$/)
  await expect(page.locator('.workspace-shell--hero')).toHaveCount(0)
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
  await expect(page.locator('nav.student-top-navigation')).toHaveCount(0)
  expect(errors).toEqual([])
})

test('全生产路由在默认桌面视口没有新增错误或横向溢出', async ({ page }) => {
  test.setTimeout(150_000)
  await page.setViewportSize({ width: 1280, height: 900 })
  const failures: string[] = []
  let currentPath = ''
  page.on('console', (message) => { if (message.type() === 'error') failures.push(`${currentPath}: console ${message.text()}`) })
  page.on('pageerror', (error) => failures.push(`${currentPath}: page ${error.message}`))
  page.on('response', (response) => { if (response.status() >= 400) failures.push(`${currentPath}: ${response.status()} ${response.url()}`) })

  async function audit(path: string) {
    currentPath = path
    const start = failures.length
    await assertProductionRoute(page, path)
    await page.waitForTimeout(180)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), { message: `横向溢出: ${path}` }).toBeTruthy()
    expect(failures.slice(start), `路由存在新增浏览器错误: ${path}`).toEqual([])
  }

  await login(page, 'student', '/student/home')
  const studentProject = await findProjectWithTasks(page)
  const studentRoutes = [
    '/student/home', '/student/projects', '/student/ai', '/student/cases',
    '/student/competitions', '/student/announcements', '/student/invitations',
    '/student/notifications',
    ...(studentProject ? [
      `/student/projects/${studentProject.id}`,
      `/student/projects/${studentProject.id}/map`,
      `/student/projects/${studentProject.id}/materials`,
      `/student/projects/${studentProject.id}/report`,
      `/student/projects/${studentProject.id}/tasks/${studentProject.taskId}`,
      `/student/public-applications?projectId=${studentProject.id}`,
    ] : []),
  ]
  for (const path of studentRoutes) await audit(path)

  await page.context().clearCookies()
  await login(page, 'teacher', '/teacher/home')
  const teacherProject = await findProjectWithTasks(page)
  const teacherRoutes = [
    '/teacher/home', '/teacher/pool', '/teacher/projects', '/teacher/reviews',
    '/teacher/members', '/teacher/cases', '/teacher/competitions', '/teacher/announcements',
    '/teacher/notifications',
    ...(teacherProject ? [`/teacher/projects/${teacherProject.id}`, `/teacher/projects/${teacherProject.id}/template`] : []),
  ]
  const reviewId = await findFirstId(page, '/api/material-revisions/pending_reviews/')
  if (reviewId) teacherRoutes.push(`/teacher/reviews/${reviewId}`)
  for (const path of teacherRoutes) await audit(path)

  await page.context().clearCookies()
  await login(page, 'platform_admin', '/platform/home')
  const schoolId = await findFirstId(page, '/api/schools/')
  const platformRoutes = [
    '/platform/home', '/platform/schools', '/platform/competitions', '/platform/announcements',
    '/platform/cases', '/platform/settings', '/platform/ai-agents',
    ...(schoolId ? [`/platform/schools/${schoolId}`] : []),
  ]
  for (const path of platformRoutes) await audit(path)
})

test('学生可以进入项目和 AI 工作台', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  await expect(page.getByRole('heading', { name: '我的项目', exact: true })).toBeVisible()
  await page.goto('/student/ai')
  await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
  await expect(page.locator('.workspace-sidebar a[aria-current="page"]')).toContainText('灵思 AI')
  await expect(page.getByText('研究工作台')).toBeVisible()
  await expect(page.getByRole('heading', { name: '灵思 AI', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: /开题/ })).toBeVisible()
  await expect(page.getByRole('tab', { name: /^研究 / })).toBeVisible()
  await expect(page.getByRole('tab', { name: /^成果表达 / })).toBeVisible()
  await expect(page.locator('.ai-workbench-composer')).toHaveCount(1)
  const newConversation = page.getByRole('button', { name: '新建对话', exact: true })
  if (await newConversation.count()) await newConversation.click()
  await expect(page.locator('.ai-workbench-page--new')).toHaveCount(1)
  await expect(page.getByRole('button', { name: '历史会话' })).toHaveCount(1)
  await expect(page.getByRole('button', { name: '更多能力' })).toHaveCount(0)
  await expect(page.locator('.ai-context-drawer, .ai-tool-picker')).toHaveCount(0)
})

test('已有课题可以直接创建项目', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  await page.getByRole('button', { name: /新建项目/ }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  const title = `E2E 已有课题 ${Date.now()}`
  await dialog.locator('input').first().fill(title)
  await dialog.locator('textarea').first().fill('比较校园不同位置的积水持续时间。')
  await dialog.getByRole('button', { name: '创建项目', exact: true }).click()
  await expect(page.locator('aside.feedback-banner[role="status"]')).toContainText('项目已创建')
  await page.getByRole('button', { name: '查看项目' }).click()
  await expect(page).toHaveURL(/\/student\/projects\/\d+\/map$/)
  await expect(page.getByRole('heading', { name: title })).toBeVisible()
})

test('无课题可以进入 AI 对话工作台，不需要先填写补充表单', async ({ page }) => {
  await login(page, 'student', '/student/projects?create=1')
  await page.getByRole('dialog').getByRole('tab', { name: /AI 开题/ }).click()
  await expect(page).toHaveURL(/\/student\/ai\?mode=opening/)

  await expect(page.getByRole('heading', { name: '灵思 AI', exact: true })).toBeVisible()
  await expect(page.locator('.ai-workbench-page--new')).toHaveCount(1)
  await expect(page.getByRole('button', { name: '历史会话' })).toBeVisible()
  await expect(page.getByPlaceholder('写下你的观察或研究想法…')).toBeVisible()
  await expect(page.getByText('补充信息（可选）')).toHaveCount(0)
  await expect(page.getByLabel('研究问题工作台')).toHaveCount(0)
  await expect(page.locator('.ai-empty-state, .ai-project-selector')).toHaveCount(0)
})

test('研究旅程以五个章节呈现，当前章节默认展开', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  const project = await findProjectWithTasks(page)
  test.skip(!project, '当前演示账号没有可检查任务的项目')
  await page.goto(`/student/projects/${project!.id}/map`)
  await expect(page.getByRole('heading', { name: '研究章节', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '研究报告', exact: true })).toBeVisible()
  await expect(page.locator('.demo-accordion-row').first()).toBeVisible()
  await expect(page.locator('.demo-accordion-row.is-open')).toHaveCount(1)
  await expect(page.locator('.demo-accordion-row.is-open .demo-task-mini').first()).toBeVisible()
  for (const viewport of [{ width: 1280, height: 900 }, { width: 1440, height: 960 }]) {
    await page.setViewportSize(viewport)
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  }
})

test('学生项目从研究进程可以进入任务和报告装配，材料旧入口回到研究进程', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  const project = await findProjectWithTasks(page)
  test.skip(!project, '当前演示账号没有可检查任务的项目')

  await page.goto(`/student/projects/${project!.id}/map`)
  await expect(page.locator('.demo-accordion-row').first()).toBeVisible()
  const openTask = page.locator('.demo-accordion-row.is-open a.text-link').first()
  await expect(openTask).toBeVisible()
  await openTask.click()
  await expect(page).toHaveURL(/\/student\/projects\/\d+\/tasks\/\d+$/)
  await expect(page.locator('.demo-task-aside')).toContainText('需要一点思路？')

  await page.goto(`/student/projects/${project!.id}/materials`)
  await expect(page).toHaveURL(new RegExp(`/student/projects/${project!.id}/map$`))
  await expect(page.locator('.page-header .eyebrow')).toHaveText('研究进程')
  await expect(page.getByText('材料记录', { exact: true })).toHaveCount(0)

  await page.goto(`/student/projects/${project!.id}/report`)
  await expect(page.locator('.demo-report-grid')).toBeVisible()
  await expect(page.getByRole('heading', { name: '导出报告', exact: true })).toBeVisible()
})

test('教师指导项目列表使用项目卡片并保留唯一详情入口', async ({ page }) => {
  await login(page, 'teacher', '/teacher/projects')
  await expect(page.getByRole('heading', { name: '指导项目', exact: true })).toBeVisible()
  await expect(page.getByRole('tab', { name: /指导中/ })).toHaveAttribute('aria-selected', 'true')
  const cards = page.locator('#teacher-project-list .project-card')
  if (await cards.count()) {
    await expect(cards.locator('.project-card__summary')).toHaveCount(await cards.count())
    await expect(cards.locator('.project-card__actions')).toHaveCount(await cards.count())
  }
})

test('学生 AI 三种模式共享聊天布局并隐藏技术 Agent', async ({ page }) => {
  await login(page, 'student', '/student/ai')

  for (const viewport of [{ width: 1280, height: 768 }, { width: 1440, height: 900 }]) {
    await page.setViewportSize(viewport)
    await page.goto('/student/ai')
    const modes = page.getByRole('tab', { name: /开题|研究|成果表达/ })
    await expect(modes).toHaveCount(3)
    for (const label of ['开题', '研究', '成果表达']) {
      await page.getByRole('tab', { name: new RegExp(`^${label}`) }).click()
      await expect(page.getByRole('tab', { name: new RegExp(`^${label}`) })).toHaveAttribute('aria-selected', 'true')
      await expect(page.locator('.ai-agent-strip, .ai-agent-more, [data-agent-rail]')).toHaveCount(0)
      await expect(page.locator('.ai-workbench-composer')).toHaveCount(1)
      await expect(page.locator('.ai-context-drawer, .ai-tool-picker')).toHaveCount(0)
      await expect(page.locator('.ai-project-selector')).toHaveCount(0)
    }
  }
})

test('核心角色页面在目标视口内不产生文档级横向溢出', async ({ page }) => {
  test.setTimeout(180_000)
  const viewports = [
    { width: 1280, height: 900 },
    { width: 1440, height: 960 },
  ]

  async function auditRouteAtViewports(path: string) {
    await page.goto(path)
    await expect(page).not.toHaveURL(/\/login/)
    for (const viewport of viewports) {
      await page.setViewportSize(viewport)
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), { message: `横向溢出: ${path} @ ${viewport.width}` }).toBeTruthy()
    }
  }

  await login(page, 'student', '/student/projects')
  await expect(page.getByRole('heading', { name: '我的项目', exact: true })).toBeVisible()
  const studentProject = await findProjectWithTasks(page)
  const studentRoutes = [
    '/student/home', '/student/projects', '/student/ai', '/student/cases',
    '/student/competitions', '/student/announcements', '/student/invitations',
    '/student/notifications',
    ...(studentProject ? [
      `/student/projects/${studentProject.id}`,
      `/student/projects/${studentProject.id}/map`,
      `/student/projects/${studentProject.id}/materials`,
      `/student/projects/${studentProject.id}/report`,
      `/student/projects/${studentProject.id}/tasks/${studentProject.taskId}`,
      `/student/public-applications?projectId=${studentProject.id}`,
    ] : []),
  ]
  for (const path of studentRoutes) await auditRouteAtViewports(path)

  await page.context().clearCookies()
  await login(page, 'teacher', '/teacher/reviews')
  await expect(page.getByRole('heading', { name: '学生材料审核' })).toBeVisible()
  const teacherProject = await findProjectWithTasks(page)
  const teacherReviewId = await findFirstId(page, '/api/material-revisions/pending_reviews/')
  const teacherRoutes = [
    '/teacher/home', '/teacher/pool', '/teacher/projects', '/teacher/reviews',
    '/teacher/members', '/teacher/cases', '/teacher/competitions', '/teacher/announcements',
    '/teacher/notifications',
    ...(teacherProject ? [`/teacher/projects/${teacherProject.id}`, `/teacher/projects/${teacherProject.id}/template`] : []),
    ...(teacherReviewId ? [`/teacher/reviews/${teacherReviewId}`] : ['/teacher/reviews/999999']),
  ]
  for (const path of teacherRoutes) await auditRouteAtViewports(path)

  await page.context().clearCookies()
  await login(page, 'platform_admin', '/platform/schools')
  await expect(page.getByRole('heading', { name: '学校空间', exact: true })).toBeVisible()
  const schoolId = await findFirstId(page, '/api/schools/')
  const platformRoutes = [
    '/platform/home', '/platform/schools', '/platform/competitions', '/platform/announcements',
    '/platform/cases', '/platform/settings', '/platform/ai-agents',
    ...(schoolId ? [`/platform/schools/${schoolId}`] : []),
  ]
  for (const path of platformRoutes) await auditRouteAtViewports(path)

  await page.context().clearCookies()
  for (const path of ['/', '/login', '/register']) {
    await page.goto(path)
    for (const viewport of viewports) {
      await page.setViewportSize(viewport)
      await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), { message: `公共页面横向溢出: ${path} @ ${viewport.width}` }).toBeTruthy()
    }
  }
})

test('教师和平台管理员分别进入各自工作台', async ({ page }) => {
  await login(page, 'teacher', '/teacher/reviews')
  await expect(page.getByRole('heading', { name: '学生材料审核' })).toBeVisible()

  await page.context().clearCookies()
  await login(page, 'platform_admin', '/platform/competitions')
  await expect(page.getByRole('heading', { name: '赛事管理', exact: true })).toBeVisible()
})

test('关键页面没有本轮引入的浏览器控制台错误', async ({ page }) => {
  const errors: string[] = []
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('pageerror', (error) => errors.push(error.message))
  page.on('response', (response) => {
    if (response.status() >= 400) errors.push(`${response.status()} ${response.url()}`)
  })
  await login(page, 'student', '/student/projects')
  await expect(page.getByRole('heading', { name: '我的项目', exact: true })).toBeVisible()
  const conversationsLoaded = page.waitForResponse((response) => response.request().method() === 'GET' && response.url().includes('/api/ai-conversations/') && response.status() < 400)
  await page.goto('/student/ai?mode=brainstorm&agent=proposal-topic')
  await expect(page.locator('.ai-workbench-composer__textarea')).toBeVisible()
  await conversationsLoaded
  await page.context().clearCookies()
  await login(page, 'teacher', '/teacher/projects')
  await expect(page.getByRole('heading', { name: '指导项目', exact: true })).toBeVisible()
  expect(errors).toEqual([])
})
