import { expect, test, type Page } from '@playwright/test'
import { login, seedCoreFlow } from './realAuth'

const outputDir = 'artifacts/ui-full-site'

type Role = 'student' | 'teacher' | 'platform_admin'
type DemoRole = '公共入口' | '学生端' | '教师端' | '平台端'
type Surface = { key: string; route: string; demoRole: DemoRole; demoPage: string }

test.beforeAll(seedCoreFlow)

async function firstId(page: Page, endpoint: string) {
  return page.evaluate(async (url) => {
    const response = await fetch(url, { credentials: 'include' })
    if (!response.ok) return null
    const data = await response.json() as Array<{ id: number }>
    return Array.isArray(data) && data.length ? data[0].id : null
  }, endpoint)
}

async function projectWithTask(page: Page) {
  return page.evaluate(async () => {
    const projects = await (await fetch('/api/projects/', { credentials: 'include' })).json() as Array<{ id: number }>
    for (const project of projects) {
      const tasks = await (await fetch(`/api/project-tasks/?project=${project.id}`, { credentials: 'include' })).json() as Array<{ id: number }>
      if (Array.isArray(tasks) && tasks.length) return { id: project.id, taskId: tasks[0].id }
    }
    return projects.length ? { id: projects[0].id, taskId: null } : null
  })
}

async function settle(page: Page) {
  await page.waitForLoadState('domcontentloaded')
  await page.locator('.loading-state').waitFor({ state: 'hidden', timeout: 15_000 }).catch(() => undefined)
  await page.waitForTimeout(220)
  await page.evaluate(() => scrollTo(0, 0))
}

async function assertSharedPrimitives(page: Page, route: string) {
  const snapshot = await page.evaluate(() => {
    const inspect = (selector: string) => [...document.querySelectorAll<HTMLElement>(selector)].slice(0, 5).map((element) => {
      const style = getComputedStyle(element)
      return {
        border: style.border,
        borderRadius: style.borderRadius,
        display: style.display,
        minHeight: parseFloat(style.minHeight) || 0,
        padding: style.padding,
      }
    })
    return {
      inputs: inspect('.input'),
      selects: inspect('.select'),
      chips: inspect('.chip'),
      statuses: inspect('.status-tag'),
      rows: inspect('.list-row'),
      tables: inspect('.table-wrap'),
      headers: inspect('table th'),
      unknownStatusTags: document.querySelectorAll('statustag').length,
    }
  })

  for (const control of [...snapshot.inputs, ...snapshot.selects]) {
    expect(control.minHeight, `原生筛选控件未套用方案 B: ${route}`).toBeGreaterThanOrEqual(36)
    expect(control.border, `原生筛选控件仍使用默认边框: ${route}`).not.toMatch(/inset|2px/i)
    expect(control.borderRadius, `筛选控件缺少统一圆角: ${route}`).not.toBe('0px')
  }
  for (const pill of [...snapshot.chips, ...snapshot.statuses]) {
    expect(pill.display, `状态/分类标签未显示为胶囊: ${route}`).toMatch(/flex/)
    expect(pill.borderRadius, `状态/分类标签缺少胶囊圆角: ${route}`).toMatch(/999px|12px/)
  }
  for (const row of snapshot.rows) {
    expect(row.display, `列表行未使用共享布局: ${route}`).toBe('flex')
    expect(row.padding).toContain('15px')
  }
  for (const header of snapshot.headers) {
    expect(header.padding, `表头未使用方案 B 间距: ${route}`).toContain('12px')
  }
  expect(snapshot.unknownStatusTags, `存在未解析的 StatusTag: ${route}`).toBe(0)
}

async function openDemo(page: Page, role: DemoRole, label: string) {
  await page.goto('/design-demo.html')
  const roleKey = ({ '公共入口': 'public', '学生端': 'student', '教师端': 'teacher', '平台端': 'platform' } as const)[role]
  await page.evaluate((nextRole) => {
    const trigger = document.createElement('button')
    trigger.dataset.role = nextRole
    document.body.appendChild(trigger)
    trigger.click()
    trigger.remove()
  }, roleKey)
  const nav = page.locator('.nav-item').filter({ hasText: label }).first()
  if (await nav.count()) await nav.click()
  await page.waitForTimeout(80)
  await page.evaluate(() => scrollTo(0, 0))
}

async function captureComparison(reference: Page, implementation: Page, compare: Page, viewport: { width: number; height: number }, surface: Surface) {
  await openDemo(reference, surface.demoRole, surface.demoPage)
  await implementation.goto(surface.route)
  await settle(implementation)
  if (!surface.route.endsWith('/login') && surface.route !== '/login') {
    await expect(implementation).not.toHaveURL(/\/login$/)
  }
  await expect.poll(() => implementation.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), { message: `横向溢出: ${surface.route} @ ${viewport.width}` }).toBeTruthy()
  await assertSharedPrimitives(implementation, surface.route)
  const clippedElements = await implementation.evaluate(() => [...document.querySelectorAll<HTMLElement>('body *')].flatMap((element) => {
    const style = getComputedStyle(element)
    if (style.display === 'none' || style.visibility === 'hidden' || Number(style.opacity) === 0) return []
    const rect = element.getBoundingClientRect()
    if (!rect.width || !rect.height) return []
    let ancestor = element.parentElement
    while (ancestor && ancestor !== document.body && ancestor !== document.documentElement) {
      const overflow = getComputedStyle(ancestor)
      if (/(auto|scroll|hidden|clip)/.test(`${overflow.overflowX} ${overflow.overflow}`)) return []
      ancestor = ancestor.parentElement
    }
    return rect.left < -2 || rect.right > window.innerWidth + 2
      ? [`${element.tagName.toLowerCase()}.${element.className || '(no-class)'} [${Math.round(rect.left)}, ${Math.round(rect.right)}]`]
      : []
  }).slice(0, 8))
  expect(clippedElements, `可见元素越出桌面画布: ${surface.route} @ ${viewport.width}`).toEqual([])

  if (surface.key === 'student-task') {
    const geometry = await implementation.locator('.demo-task-layout').evaluate((node) => {
      const columns = getComputedStyle(node).gridTemplateColumns.split(' ').filter(Boolean)
      const paperWidth = node.querySelector<HTMLElement>('.demo-task-main')?.getBoundingClientRect().width ?? 0
      return { columns, paperWidth }
    })
    expect(geometry.columns).toHaveLength(2)
    expect(geometry.paperWidth).toBeGreaterThan(500)
  }

  const heading = implementation.locator('h1').first()
  if (await heading.count()) {
    const font = await heading.evaluate((node) => getComputedStyle(node).fontFamily)
    expect(font).not.toMatch(/Georgia|Songti|STSong|SimSun/i)
    expect(font).toContain('sans-serif')
  }

  const refBuffer = await reference.screenshot({ fullPage: true, animations: 'disabled' })
  const implBuffer = await implementation.screenshot({ fullPage: true, animations: 'disabled' })

  if (surface.key === 'platform-agents') {
    await implementation.getByRole('button', { name: /新建模板/ }).click()
    const form = implementation.locator('.agent-form')
    await expect(form).toBeVisible()
    const formGeometry = await form.evaluate((node) => {
      const style = getComputedStyle(node)
      const controls = [...node.querySelectorAll<HTMLElement>('label > input, label > textarea, label > select')]
      return {
        display: style.display,
        controls: controls.map((control) => ({ width: control.getBoundingClientRect().width, height: control.getBoundingClientRect().height })),
      }
    })
    expect(formGeometry.display).toBe('grid')
    expect(formGeometry.controls.every(({ width, height }) => width >= 180 && height >= 40)).toBeTruthy()
    await implementation.keyboard.press('Escape')
  }
  await compare.setViewportSize({ width: viewport.width * 2, height: viewport.height })
  await compare.setContent(`<!doctype html><meta charset="utf-8"><style>*{box-sizing:border-box}html,body{margin:0;background:#dfe5df;font-family:system-ui,sans-serif}.labels{position:sticky;top:0;z-index:2;display:grid;grid-template-columns:1fr 1fr;background:#1e2d26;color:white;font:600 14px/36px system-ui}.labels span{padding:0 16px}.pair{display:grid;grid-template-columns:1fr 1fr;align-items:start;gap:1px}.pair img{display:block;width:100%;height:auto;background:#f3f4f0}</style><div class="labels"><span>方案 B · ${surface.demoRole} / ${surface.demoPage}</span><span>生产页面 · ${surface.route}</span></div><div class="pair"><img src="data:image/png;base64,${refBuffer.toString('base64')}"><img src="data:image/png;base64,${implBuffer.toString('base64')}"></div>`)
  await compare.screenshot({ path: `${outputDir}/${viewport.width}-${surface.key}.png`, fullPage: true, animations: 'disabled' })
}

test('全站剩余页面生成方案 B 对照矩阵并保持桌面几何', async ({ browser }) => {
  test.setTimeout(360_000)
  const context = await browser.newContext()
  const reference = await context.newPage()
  const implementation = await context.newPage()
  const compare = await context.newPage()

  const viewports = [{ width: 1280, height: 900 }, { width: 1440, height: 960 }]

  for (const viewport of viewports) {
    await reference.setViewportSize(viewport)
    await implementation.setViewportSize(viewport)

    await context.clearCookies()
    const publicSurfaces: Surface[] = [
      { key: 'public-entry', route: '/', demoRole: '公共入口', demoPage: '品牌入口' },
      { key: 'public-login', route: '/login', demoRole: '公共入口', demoPage: '登录' },
      { key: 'public-register', route: '/register', demoRole: '公共入口', demoPage: '注册' },
      { key: 'platform-login', route: '/platform/login', demoRole: '公共入口', demoPage: '登录' },
    ]
    for (const surface of publicSurfaces) await captureComparison(reference, implementation, compare, viewport, surface)

    await context.clearCookies()
    await login(implementation, 'student', '/student/projects')
    const studentProject = await projectWithTask(implementation)
    expect(studentProject, '缺少学生项目，无法完成全站视觉矩阵').toBeTruthy()
    const studentSurfaces: Surface[] = [
      { key: 'student-home', route: '/student/home', demoRole: '学生端', demoPage: '首页' },
      { key: 'student-projects', route: '/student/projects', demoRole: '学生端', demoPage: '我的项目' },
      { key: 'student-ai', route: '/student/ai', demoRole: '学生端', demoPage: 'AI 助手' },
      { key: 'student-cases', route: '/student/cases', demoRole: '学生端', demoPage: '案例与赛事' },
      { key: 'student-competitions', route: '/student/competitions', demoRole: '学生端', demoPage: '案例与赛事' },
      { key: 'student-announcements', route: '/student/announcements', demoRole: '学生端', demoPage: '案例与赛事' },
      { key: 'student-invitations', route: '/student/invitations', demoRole: '学生端', demoPage: '项目邀请' },
      { key: 'student-notifications', route: '/student/notifications', demoRole: '学生端', demoPage: '项目邀请' },
      ...(studentProject ? [
        { key: 'student-overview', route: `/student/projects/${studentProject.id}`, demoRole: '学生端' as const, demoPage: '我的项目' },
        { key: 'student-journey', route: `/student/projects/${studentProject.id}/map`, demoRole: '学生端' as const, demoPage: '研究旅程' },
        { key: 'student-materials', route: `/student/projects/${studentProject.id}/materials`, demoRole: '学生端' as const, demoPage: '材料档案' },
        { key: 'student-report', route: `/student/projects/${studentProject.id}/report`, demoRole: '学生端' as const, demoPage: '研究报告' },
        { key: 'student-applications', route: `/student/public-applications?projectId=${studentProject.id}`, demoRole: '学生端' as const, demoPage: '成果申请' },
        ...(studentProject.taskId ? [{ key: 'student-task', route: `/student/projects/${studentProject.id}/tasks/${studentProject.taskId}`, demoRole: '学生端' as const, demoPage: '当前任务' }] : []),
      ] : []),
    ]
    for (const surface of studentSurfaces) await captureComparison(reference, implementation, compare, viewport, surface)

    await context.clearCookies()
    await login(implementation, 'teacher', '/teacher/projects')
    const teacherProject = await projectWithTask(implementation)
    const reviewId = await firstId(implementation, '/api/material-revisions/pending_reviews/')
    const teacherSurfaces: Surface[] = [
      { key: 'teacher-home', route: '/teacher/home', demoRole: '教师端', demoPage: '工作台' },
      { key: 'teacher-pool', route: '/teacher/pool', demoRole: '教师端', demoPage: '项目池' },
      { key: 'teacher-projects', route: '/teacher/projects', demoRole: '教师端', demoPage: '指导项目' },
      { key: 'teacher-reviews', route: '/teacher/reviews', demoRole: '教师端', demoPage: '材料审核' },
      { key: 'teacher-members', route: '/teacher/members', demoRole: '教师端', demoPage: '成员与邀请' },
      { key: 'teacher-cases', route: '/teacher/cases', demoRole: '教师端', demoPage: '案例与公告' },
      { key: 'teacher-competitions', route: '/teacher/competitions', demoRole: '教师端', demoPage: '案例与公告' },
      { key: 'teacher-announcements', route: '/teacher/announcements', demoRole: '教师端', demoPage: '案例与公告' },
      { key: 'teacher-notifications', route: '/teacher/notifications', demoRole: '教师端', demoPage: '案例与公告' },
      ...(teacherProject ? [
        { key: 'teacher-detail', route: `/teacher/projects/${teacherProject.id}`, demoRole: '教师端' as const, demoPage: '项目详情' },
        { key: 'teacher-template', route: `/teacher/projects/${teacherProject.id}/template`, demoRole: '教师端' as const, demoPage: '材料范本' },
      ] : []),
      ...(reviewId ? [{ key: 'teacher-review-detail', route: `/teacher/reviews/${reviewId}`, demoRole: '教师端' as const, demoPage: '材料审核' }] : []),
    ]
    for (const surface of teacherSurfaces) await captureComparison(reference, implementation, compare, viewport, surface)

    await context.clearCookies()
    await login(implementation, 'platform_admin', '/platform/schools')
    const schoolId = await firstId(implementation, '/api/schools/')
    const platformSurfaces: Surface[] = [
      { key: 'platform-home', route: '/platform/home', demoRole: '平台端', demoPage: '平台概览' },
      { key: 'platform-schools', route: '/platform/schools', demoRole: '平台端', demoPage: '学校空间' },
      { key: 'platform-agents', route: '/platform/ai-agents', demoRole: '平台端', demoPage: 'AI 助手模板' },
      { key: 'platform-competitions', route: '/platform/competitions', demoRole: '平台端', demoPage: '赛事与公告' },
      { key: 'platform-announcements', route: '/platform/announcements', demoRole: '平台端', demoPage: '赛事与公告' },
      { key: 'platform-cases', route: '/platform/cases', demoRole: '平台端', demoPage: '赛事与公告' },
      { key: 'platform-settings', route: '/platform/settings', demoRole: '平台端', demoPage: '系统设置' },
      ...(schoolId ? [{ key: 'platform-school-detail', route: `/platform/schools/${schoolId}`, demoRole: '平台端' as const, demoPage: '学校详情' }] : []),
    ]
    for (const surface of platformSurfaces) await captureComparison(reference, implementation, compare, viewport, surface)
  }

  await context.close()
})
