import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

import { expect, test, type Page } from '@playwright/test'

const repoRoot = process.cwd().endsWith('/frontend') ? resolve(process.cwd(), '..') : process.cwd()
const password = 'core-e2e-pass-2026'
const studentUsername = 'core-e2e-student'
const memberUsername = 'core-e2e-member'
const directMemberUsername = 'core-e2e-direct'
const teacherUsername = 'core-e2e-teacher'
const platformUsername = 'core-e2e-platform'

type Project = { id: number; title: string; status: string; primary_teacher: number | null }
type Task = { id: number; title: string; order: number; status: string }
type ReportExport = { id: number; format: 'docx' | 'pdf'; status: string; download_url: string | null }

async function seedCoreFlow() {
  execFileSync(
    'docker',
    [
      'compose', '--env-file', '.env.integration', '--profile', 'dev', 'exec', '-T',
      '-e', 'LINGSU_E2E_SEED=1', 'backend', 'python', 'manage.py', 'seed_core_e2e',
      '--reset', '--password', password,
    ],
    { cwd: repoRoot, stdio: 'inherit' },
  )
}

async function login(page: Page, username: string, destination: string) {
  await page.context().clearCookies()
  await page.goto('/login')
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const result = await page.evaluate(async ({ username: name, password: pass }) => {
      await fetch('/api/csrf/', { credentials: 'include' })
      const csrf = decodeURIComponent(
        document.cookie.split('; ').find((item) => item.startsWith('csrftoken='))?.split('=').slice(1).join('=') ?? '',
      )
      const response = await fetch('/api/login/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
        credentials: 'include',
        body: JSON.stringify({ username: name, password: pass }),
      })
      return {
        ok: response.ok,
        status: response.status,
        body: await response.text(),
        retryAfter: Number(response.headers.get('Retry-After') || 0),
      }
    }, { username, password })
    if (result.ok) {
      await page.goto(destination)
      return
    }
    if (result.status !== 429 || attempt === 3) {
      expect(result.ok, `real login failed for ${username}: ${result.status} ${result.body}`).toBeTruthy()
    }
    await page.waitForTimeout(Math.max(result.retryAfter, 3) * 1000)
  }
}

async function getJson<T>(page: Page, path: string): Promise<T> {
  return page.evaluate(async (url) => {
    const response = await fetch(url, { credentials: 'include' })
    if (!response.ok) throw new Error(`${response.status} ${url}: ${await response.text()}`)
    return await response.json() as T
  }, `/api/${path}`)
}

async function findProject(page: Page, title: string) {
  return expect.poll(async () => {
    const projects = await getJson<Project[]>(page, 'projects/')
    return projects.find((item) => item.title === title) ?? null
  }, { timeout: 10_000 }).not.toBeNull()
}

async function projectByTitle(page: Page, title: string) {
  const projects = await getJson<Project[]>(page, 'projects/')
  const project = projects.find((item) => item.title === title)
  expect(project, `project not found: ${title}`).toBeTruthy()
  return project as Project
}

async function previewAndClaimPoolProject(page: Page, title: string, opening?: { problem?: string; plan?: string; summary?: string }) {
  const projectCard = page.locator('.project-card--pool').filter({ hasText: title })
  await expect(projectCard).toHaveCount(1)
  await projectCard.getByRole('button', { name: '查看开题报告', exact: true }).click()
  const preview = page.locator('.el-dialog:visible')
  await expect(preview).toContainText(title)
  if (opening?.problem) await expect(preview).toContainText(opening.problem)
  if (opening?.plan) await expect(preview).toContainText(opening.plan)
  if (opening?.summary) await expect(preview).toContainText(opening.summary)
  const poolBeforeClaim = await getJson<Project[]>(page, 'projects/pool/')
  expect(poolBeforeClaim.find((item) => item.title === title)?.status).toBe('unclaimed')
  await preview.getByRole('button', { name: '认领为指导项目', exact: true }).click()
  await expect(page.locator('.feedback-banner')).toContainText('项目已认领，研究任务地图已生成。')
}

async function taskList(page: Page, projectId: number) {
  return getJson<Task[]>(page, `project-tasks/?project=${projectId}`)
}

async function submitTask(page: Page, projectId: number, taskId: number, content: string, file?: { name: string; mimeType: string; buffer: Buffer }) {
  await page.goto(`/student/projects/${projectId}/tasks/${taskId}`)
  await expect(page.getByLabel('我的记录')).toBeVisible()
  await page.getByLabel('我的记录').fill(content)
  if (file) await page.locator('input[type="file"]').setInputFiles(file)
  await page.getByLabel('我已按真实项目核对以上内容').check()
  await page.getByRole('button', { name: /保存并提交|重新提交任务/, exact: false }).click()
  await expect(page.locator('.feedback-banner')).toContainText('材料已提交给主指导教师审核。', { timeout: 30_000 })
}

async function reviewLatest(page: Page, materialTitle: string, outcome: 'approve' | 'return', comment: string) {
  await page.goto('/teacher/reviews')
  const row = page.locator('a.inbox-item').filter({ hasText: materialTitle }).first()
  await expect(row).toBeVisible({ timeout: 15_000 })
  await row.click()
  await expect(page.locator('.submission-paper h2', { hasText: materialTitle })).toBeVisible()
  await page.getByLabel('审核意见').fill(comment)
  const button = outcome === 'approve' ? '通过并解锁下一任务' : '打回修订'
  await page.getByRole('button', { name: button, exact: true }).click()
  await expect(page.locator('.feedback-banner')).toContainText(
    outcome === 'approve' ? '材料已通过，下一任务已解锁。' : '修订意见已发送，学生会在任务台看到优先修复任务。',
  )
}

async function waitForReport(page: Page, projectId: number, format: 'docx' | 'pdf') {
  await expect.poll(async () => {
    const exports = await getJson<ReportExport[]>(page, `report-exports/?project=${projectId}`)
    return exports.find((item) => item.format === format && item.status === 'completed')?.id ?? null
  }, { timeout: 60_000, intervals: [1000, 2000, 3000] }).not.toBeNull()
}

test.describe('核心项目跨角色闭环', () => {
  test.describe.configure({ mode: 'serial' })

  test.beforeAll(async () => {
    await seedCoreFlow()
  })

  test('学生项目列表显示完整数据，研究进程视图导航互斥', async ({ page }) => {
    await login(page, studentUsername, '/student/projects')
    const projects = await getJson<Project[]>(page, 'projects/')
    await expect(page.locator('#student-project-list .current-project-panel')).toHaveCount(projects.length ? 1 : 0)
    await expect(page.locator('#student-project-list .student-project-card')).toHaveCount(Math.min(6, Math.max(projects.length - 1, 0)))
    await expect(page.locator('.project-pagination')).toHaveCount(Math.max(projects.length - 1, 0) > 6 ? 1 : 0)

    const projectId = projects[0].id
    await page.goto(`/student/projects/${projectId}/map`)
    await expect(page.locator('.workspace-sidebar a[aria-current="page"]')).toHaveCount(1)
    await expect(page.locator('.workspace-sidebar a[aria-current="page"]')).toContainText('研究进程')
    await page.goto(`/student/projects/${projectId}/materials`)
    await expect(page).toHaveURL(new RegExp(`/student/projects/${projectId}/map$`))
    await expect(page.locator('.workspace-sidebar a[aria-current="page"]')).toHaveCount(1)
    await expect(page.locator('.workspace-sidebar a[aria-current="page"]')).toContainText('研究进程')
    await expect(page.locator('.page-header .eyebrow')).toHaveText('研究进程')
    await expect(page.getByText('材料记录', { exact: true })).toHaveCount(0)
  })

  test('教师项目池与指导项目显示全部项目并支持认领前预览', async ({ page }) => {
    await login(page, teacherUsername, '/teacher/pool')
    const poolProjects = await getJson<Project[]>(page, 'projects/pool/')
    await expect(page.locator('.project-card--pool')).toHaveCount(poolProjects.length)
    await previewAndClaimPoolProject(page, '核心项目池验收 01', {
      problem: '如何验证校园观察问题 1 的关键变量？',
      plan: '为项目池预览准备第 1 组观察、记录和比较方案。',
      summary: '项目池确定性样本 1，用于验证教师认领前的开题信息。',
    })

    await page.goto('/teacher/projects')
    const guidedProjects = await getJson<Project[]>(page, 'projects/guided/')
    await expect(page.locator('#teacher-project-list .project-card')).toHaveCount(guidedProjects.length)
    await expect(page.locator('#teacher-project-list .project-card-grid__toolbar')).toHaveCount(1)
  })

  test('学生创建、教师审核、报告导出和校内成果申请保持真实状态', async ({ page }) => {
    test.setTimeout(180_000)
    const title = `E2E 核心闭环 ${Date.now()}`

    await login(page, studentUsername, '/student/projects?create=1')
    const dialog = page.locator('.el-dialog:visible')
    await expect(dialog).toBeVisible()
    await dialog.locator('input').first().fill(title)
    await dialog.locator('textarea').nth(0).fill('如何通过连续观察改善校园雨后积水？')
    await dialog.locator('textarea').nth(1).fill('记录不同位置的积水变化，整理证据并提出改进建议。')
    await dialog.getByRole('button', { name: '创建项目', exact: true }).click()
    await expect(page.getByText('项目已创建。')).toBeVisible()
    await findProject(page, title)
    const createdProject = await projectByTitle(page, title)

    await login(page, teacherUsername, '/teacher/pool')
    await previewAndClaimPoolProject(page, title, {
      problem: '如何通过连续观察改善校园雨后积水？',
      plan: '记录不同位置的积水变化，整理证据并提出改进建议。',
    })
    const tasks = (await taskList(page, createdProject.id)).sort((left, right) => left.order - right.order)
    expect(tasks).toHaveLength(2)

    await login(page, studentUsername, `/student/projects/${createdProject.id}/tasks/${tasks[0].id}`)
    await page.getByLabel('我的记录').fill('第一版实验日志，记录了真实观察过程。')
    await page.locator('.task-submit-row .primary-button').click()
    await expect(page.locator('.feedback-banner')).toContainText('提交前必须确认材料真实性。')
    await page.locator('input[type="file"]').setInputFiles({
      name: 'experiment-log.txt',
      mimeType: 'text/plain',
      buffer: Buffer.from('2026-08-25\n观察：雨后积水在 24 小时内减少。\n'),
    })
    await page.getByLabel('我已按真实项目核对以上内容').check()
    await expect(page.getByLabel('我已按真实项目核对以上内容')).toBeChecked()
    const submitButton = page.locator('.task-submit-row .primary-button')
    await expect(submitButton).toBeEnabled()
    await submitButton.click()
    await expect(page.locator('.feedback-banner')).toContainText('材料已提交给主指导教师审核。', { timeout: 30_000 })

    await login(page, teacherUsername, '/teacher/reviews')
    await reviewLatest(page, '实验日志', 'return', '请补充观察日期、操作过程和可核对的数据。')

    await login(page, studentUsername, `/student/projects/${createdProject.id}/tasks/${tasks[0].id}`)
    await expect(page.getByText('请补充观察日期、操作过程和可核对的数据。')).toBeVisible()
    await page.getByLabel('我的记录').fill('修订后的实验日志：2026-08-25，记录积水深度从 4cm 降至 1cm。')
    await page.getByLabel('我已按真实项目核对以上内容').check()
    await page.getByRole('button', { name: '重新提交任务', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('材料已提交给主指导教师审核。', { timeout: 30_000 })

    await login(page, teacherUsername, '/teacher/reviews')
    await reviewLatest(page, '实验日志', 'approve', '记录完整，证据可以复核。')

    await login(page, studentUsername, `/student/projects/${createdProject.id}/tasks/${tasks[1].id}`)
    await submitTask(page, createdProject.id, tasks[1].id, '整理后的研究记录：不同位置的积水变化已完成对比。')

    await login(page, teacherUsername, '/teacher/reviews')
    await reviewLatest(page, '研究记录', 'approve', '研究记录与问题对应，准予通过。')
    await expect.poll(async () => (await projectByTitle(page, title)).status, { timeout: 15_000 }).toBe('completed')

    await login(page, studentUsername, `/student/projects/${createdProject.id}/report`)
    await expect(page.getByRole('button', { name: '导出 Word', exact: true })).toBeEnabled()
    await page.getByRole('button', { name: '导出 Word', exact: true }).click()
    await expect(page.getByText('DOCX 导出任务已排队。')).toBeVisible()
    await waitForReport(page, createdProject.id, 'docx')
    await page.reload()
    const docxRow = page.locator('.demo-list-row').filter({ hasText: 'DOCX' })
    await expect(docxRow).toContainText('已完成')
    const [docxDownload] = await Promise.all([page.waitForEvent('download'), docxRow.getByRole('link', { name: '下载' }).click()])
    expect(docxDownload.suggestedFilename()).toMatch(/\.docx$/)

    await page.getByRole('button', { name: '导出 PDF', exact: true }).click()
    await waitForReport(page, createdProject.id, 'pdf')
    await page.reload()
    const pdfRow = page.locator('.demo-list-row').filter({ hasText: 'PDF' })
    await expect(pdfRow).toContainText('已完成')
    const [pdfDownload] = await Promise.all([page.waitForEvent('download'), pdfRow.getByRole('link', { name: '下载' }).click()])
    expect(pdfDownload.suggestedFilename()).toMatch(/\.pdf$/)

    await page.goto(`/student/public-applications?projectId=${createdProject.id}`)
    await expect(page.getByRole('button', { name: '申请公开案例', exact: true })).toBeEnabled()
    await page.getByRole('button', { name: '申请公开案例', exact: true }).click()
    const caseDialog = page.locator('.el-dialog:visible')
    await caseDialog.locator('textarea').first().fill('校园积水观察项目的研究过程与结果摘要。')
    await caseDialog.locator('input[type="checkbox"]').first().check()
    await caseDialog.getByRole('button', { name: '提交教师审核', exact: true }).click()
    await expect(page.getByText('公开申请已提交。')).toBeVisible()

    await login(page, teacherUsername, '/teacher/cases')
    const caseCard = page.locator('.demo-content-card').filter({ hasText: title })
    await expect(caseCard).toBeVisible()
    await caseCard.getByRole('button', { name: '审核通过', exact: true }).click()
    await expect(page.getByText('案例已审核通过并发布。')).toBeVisible()

    await login(page, studentUsername, '/student/notifications')
    await expect(page.getByText(/材料「(实验日志|研究记录)」已通过审核/).first()).toBeVisible()
  })

  test('学生邀请、教师确认、教师直接分配和通知已读状态保持真实', async ({ page }) => {
    test.setTimeout(180_000)

    await login(page, studentUsername, '/student/projects')
    const invitedProject = await projectByTitle(page, '核心闭环验收项目')

    await login(page, teacherUsername, '/teacher/pool')
    await previewAndClaimPoolProject(page, invitedProject.title)

    const invitedTasks = (await taskList(page, invitedProject.id)).sort((left, right) => left.order - right.order)
    expect(invitedTasks.length).toBeGreaterThanOrEqual(1)
    await login(page, studentUsername, `/student/projects/${invitedProject.id}/tasks/${invitedTasks[0].id}`)
    await submitTask(page, invitedProject.id, invitedTasks[0].id, '分片上传实验日志：记录连续观察数据。', {
      name: 'chunked-experiment-log.txt',
      mimeType: 'text/plain',
      buffer: Buffer.alloc(8 * 1024 * 1024 + 1, 65),
    })
    await login(page, teacherUsername, '/teacher/reviews')
    await reviewLatest(page, '实验日志', 'approve', '分片附件已扫描通过，记录可以复核。')

    await login(page, studentUsername, `/student/projects/${invitedProject.id}`)
    await page.getByRole('button', { name: '邀请项目成员', exact: true }).click()
    const studentInviteDialog = page.locator('.el-dialog:visible')
    await studentInviteDialog.getByLabel('姓名或账号').fill(memberUsername)
    await studentInviteDialog.getByRole('button', { name: '搜索', exact: true }).click()
    await expect(studentInviteDialog.getByText('协作学生')).toBeVisible()
    await studentInviteDialog.getByRole('button', { name: '发出邀请', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('项目邀请已发出。')

    await login(page, memberUsername, '/student/invitations')
    await expect(page.getByText(`邀请你加入「${invitedProject.title}」`)).toBeVisible()
    await page.getByRole('button', { name: '接受邀请', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('邀请已接受。')

    await login(page, studentUsername, '/student/notifications')
    const acceptedNotice = page.getByRole('button', { name: /接受了项目「核心闭环验收项目」/ }).first()
    await expect(acceptedNotice).toBeVisible()
    await acceptedNotice.click()
    await expect(page).toHaveURL(new RegExp(`/student/projects/${invitedProject.id}/map$`))
    await page.goto('/student/notifications')
    await page.getByRole('button', { name: /全部已读/ }).click()
    await expect(page.getByRole('button', { name: /^未读/ })).toContainText('0')
    const leaderNotifications = await getJson<Array<{ is_read: boolean }>>(page, 'notifications/')
    expect(leaderNotifications.every((item) => item.is_read)).toBeTruthy()

    await login(page, teacherUsername, `/teacher/members?projectId=${invitedProject.id}`)
    const pendingMember = page.locator('.pilot-list-row').filter({ hasText: memberUsername }).first()
    await expect(pendingMember).toBeVisible()
    await pendingMember.getByRole('button', { name: '确认加入', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('成员已加入项目团队。')

    await login(page, memberUsername, `/student/projects/${invitedProject.id}`)
    await expect(page.locator('.journey-overview')).toContainText('研究小组')
    const memberProject = await getJson<Project>(page, `projects/${invitedProject.id}/`)
    expect(memberProject.members.some((item) => item.username === memberUsername)).toBeTruthy()

    await login(page, teacherUsername, `/teacher/members?projectId=${invitedProject.id}`)
    await page.getByRole('button', { name: '邀请成员', exact: true }).click()
    const directAssignDialog = page.locator('.el-dialog:visible')
    await directAssignDialog.getByLabel('姓名或账号').fill(directMemberUsername)
    await directAssignDialog.getByRole('button', { name: '搜索', exact: true }).click()
    await expect(directAssignDialog.getByText('教师分配学生')).toBeVisible()
    await directAssignDialog.getByRole('button', { name: '加入项目', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('已将该同学加入项目。')

    await login(page, directMemberUsername, `/student/projects/${invitedProject.id}`)
    await expect(page.locator('.journey-overview')).toContainText('研究小组')
    const directProject = await getJson<Project>(page, `projects/${invitedProject.id}/`)
    expect(directProject.members.some((item) => item.username === directMemberUsername)).toBeTruthy()
    await page.goto('/student/notifications')
    await expect(page.getByRole('button', { name: /教师已将你加入项目/ })).toBeVisible()
    await page.getByRole('button', { name: /全部已读/ }).click()
    await page.reload()
    const directNotifications = await getJson<Array<{ is_read: boolean }>>(page, 'notifications/')
    expect(directNotifications.every((item) => item.is_read)).toBeTruthy()
  })

  test('教师公域邀请、学生同意、平台发布和案例治理保持真实', async ({ page }) => {
    test.setTimeout(120_000)
    await login(page, studentUsername, '/student/projects')
    const project = await projectByTitle(page, '核心公域验收项目')

    await login(page, teacherUsername, `/teacher/projects/${project.id}`)
    await expect(page.getByRole('button', { name: '邀请全平台展示', exact: true })).toBeVisible()
    await page.getByRole('button', { name: '邀请全平台展示', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认发出邀请', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('全平台展示邀请已发出。')

    await login(page, studentUsername, `/student/public-applications?projectId=${project.id}`)
    const applicationRow = page.locator('.list-row').filter({ hasText: project.title })
    await expect(applicationRow).toBeVisible()
    await applicationRow.getByRole('button', { name: '同意全平台展示', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认同意', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('已同意全平台展示。')

    await login(page, platformUsername, '/platform/cases')
    const governanceCard = page.locator('.demo-governance-grid article').filter({ hasText: project.title })
    await expect(governanceCard).toBeVisible()
    await governanceCard.getByRole('button', { name: '通过并发布', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认发布', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('案例已通过平台审核并发布。')

    await login(page, studentUsername, '/student/cases')
    await expect(page.getByText(project.title, { exact: true })).toBeVisible()
    await login(page, studentUsername, '/student/notifications')
    await expect(page.getByRole('button', { name: new RegExp(`成果「${project.title}」已发布到全平台`) })).toBeVisible()

    await login(page, platformUsername, '/platform/cases')
    const publishedCard = page.locator('.demo-governance-grid article').filter({ hasText: project.title })
    await publishedCard.getByRole('button', { name: '下架', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认下架', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('案例已下架。')

    await login(page, studentUsername, '/student/cases')
    await expect(page.getByText(project.title, { exact: true })).not.toBeVisible()

    await login(page, platformUsername, '/platform/cases')
    const offlineCard = page.locator('.demo-governance-grid article').filter({ hasText: project.title })
    await offlineCard.getByRole('button', { name: '恢复公开', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认恢复', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('案例已恢复公开。')
    await login(page, studentUsername, '/student/cases')
    await expect(page.getByText(project.title, { exact: true })).toBeVisible()
  })

  test('平台学校、赛事、公告和 AI 模板管理保持真实筛选与状态变化', async ({ page }) => {
    test.setTimeout(120_000)
    const suffix = Date.now()
    const schoolName = `E2E 管理学校 ${suffix}`
    const competitionTitle = `E2E 管理赛事 ${suffix}`
    const announcementTitle = `E2E 管理公告 ${suffix}`
    const agentName = `E2E 管理助手 ${suffix}`
    const agentKey = `e2e-management-${suffix}`

    await login(page, platformUsername, '/platform/schools')
    await page.getByRole('button', { name: '添加学校', exact: true }).click()
    const schoolDialog = page.locator('.el-dialog:visible')
    await schoolDialog.getByLabel('学校名称').fill(schoolName)
    await schoolDialog.getByRole('button', { name: '创建学校', exact: true }).click()
    await page.getByLabel('搜索学校名称').fill(schoolName)
    const schoolRow = page.locator('tbody tr').filter({ hasText: schoolName })
    await expect(schoolRow).toBeVisible()
    await schoolRow.locator('input[role="switch"]').evaluate((element) => (element as HTMLInputElement).click())
    await page.locator('.el-dialog:visible').getByRole('button', { name: '停用并只读', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('学校已停用')

    await page.goto('/platform/competitions')
    await page.getByRole('button', { name: '发布赛事', exact: true }).click()
    const competitionDialog = page.locator('.el-dialog:visible')
    await competitionDialog.getByLabel('赛事名称').fill(competitionTitle)
    await competitionDialog.getByLabel('赛事说明').fill('验证平台赛事从草稿到发布的状态变化。')
    await competitionDialog.getByRole('button', { name: '保存草稿', exact: true }).click()
    const competitionCard = page.locator('.platform-content-grid article').filter({ hasText: competitionTitle })
    await expect(competitionCard).toBeVisible()
    await competitionCard.getByRole('button', { name: '发布', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认发布', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('赛事已发布到全平台。')

    await page.goto('/platform/announcements')
    await page.getByRole('button', { name: '发布公告', exact: true }).click()
    const announcementDialog = page.locator('.el-dialog:visible')
    await announcementDialog.getByLabel('公告标题').fill(announcementTitle)
    await announcementDialog.getByLabel('公告正文').fill('验证平台公告发布后可以在列表中检索。')
    await announcementDialog.getByRole('button', { name: '发布公告', exact: true }).click()
    await page.getByLabel('搜索系统公告').fill(announcementTitle)
    await expect(page.locator('.platform-content-grid article').filter({ hasText: announcementTitle })).toBeVisible()

    await page.goto('/platform/ai-agents')
    await page.getByRole('button', { name: /新建模板/ }).click()
    const agentForm = page.locator('.agent-form')
    await agentForm.getByLabel(/key/).fill(agentKey)
    await agentForm.getByLabel('名称').fill(agentName)
    await agentForm.getByLabel('系统指令').fill('你是一个测试用的研究助手。')
    await agentForm.getByLabel('提示词模板').fill('请基于 {project_title} 给出一条可核对建议。')
    await agentForm.getByRole('button', { name: '保存', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('AI 模板已保存。')
    await page.locator('.agent-filters input[placeholder="搜索模板名称"]').fill(agentName)
    const agentRow = page.locator('.demo-agent-table tbody tr').filter({ hasText: agentName })
    await expect(agentRow).toBeVisible()
    await agentRow.getByRole('button', { name: '停用', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('AI 模板已停用。')
    await agentRow.getByRole('button', { name: '编辑', exact: true }).click()
    await page.locator('.agent-form').getByRole('button', { name: '删除模板', exact: true }).click()
    await page.locator('.el-dialog:visible').getByRole('button', { name: '确认删除', exact: true }).click()
    await expect(page.locator('.feedback-banner')).toContainText('AI 模板已删除。')
  })

  test('灵思 AI 受控响应支持失败重试、流式结果、人工编辑和保存草稿', async ({ page }) => {
    test.setTimeout(90_000)
    await login(page, studentUsername, '/student/projects')
    const project = await projectByTitle(page, '核心闭环验收项目')
    if (project.primary_teacher === null) {
      await login(page, teacherUsername, '/teacher/pool')
      await previewAndClaimPoolProject(page, project.title)
    }

    await login(page, studentUsername, `/student/ai?mode=research&projectId=${project.id}`)
    await expect(page.locator('.ai-workbench-composer__textarea')).toBeVisible()
    await page.getByRole('tab', { name: /^成果表达/ }).click()
    await expect(page).toHaveURL(/\/student\/ai\?mode=defense&projectId=/)
    await expect(page.locator('.ai-workbench-composer__textarea')).toBeVisible()
    await page.goto(`/student/ai?mode=research&projectId=${project.id}`)

    let messageRequests = 0
    let streamRequests = 0
    const assistantId = 970001
    const generationLogId = 970101
    const queuedMessage = (artifact: Record<string, unknown> | null = null) => ({
      id: assistantId,
      role: 'assistant',
      content: '',
      status: 'queued',
      generation_log: generationLogId,
      artifact_payload: artifact,
      verification_items: [],
      error_message: '',
      created_at: new Date().toISOString(),
    })
    const sse = (events: Array<{ event: string; data: Record<string, unknown> }>) => events.map((item, index) => `id: ${index + 1}-0\nevent: ${item.event}\ndata: ${JSON.stringify(item.data)}\n\n`).join('')

    await page.route(/\/api\/ai-conversations\/\d+\/messages\/$/, async (route) => {
      if (route.request().method() !== 'POST') return route.continue()
      messageRequests += 1
      await route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify(queuedMessage()) })
    })
    await page.route(/\/api\/ai-conversations\/\d+\/messages\/\d+\/retry\/$/, async (route) => {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(queuedMessage()) })
    })
    await page.route(/\/api\/ai-conversations\/\d+\/messages\/\d+\/stream\/$/, async (route) => {
      streamRequests += 1
      const body = streamRequests === 1
        ? sse([
            { event: 'message.started', data: {} },
            { event: 'message.delta', data: { delta: '受控响应准备中…' } },
            { event: 'message.error', data: { error: '受控替身暂时失败' } },
          ])
        : sse([
            { event: 'message.started', data: {} },
            { event: 'message.delta', data: { delta: '围绕当前项目材料整理出的建议。' } },
            { event: 'message.artifact', data: {
              artifact_payload: { title: '研究记录建议', draft: '建议补充观察日期和可核对数据。', next_action: '核对后再保存' },
              verification_items: [{ item: '核对观察日期', status: 'pending' }],
            } },
            { event: 'message.done', data: { message_id: assistantId } },
          ])
      await route.fulfill({ status: 200, contentType: 'text/event-stream', body })
    })
    let savedPayload: Record<string, unknown> | null = null
    await page.route(/\/api\/ai-logs\/970101\/save_as_material\/$/, async (route) => {
      savedPayload = JSON.parse(route.request().postData() || '{}') as Record<string, unknown>
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({ id: 970201, status: 'draft', content: savedPayload.content }),
      })
    })

    await page.locator('.ai-workbench-composer__textarea').fill('请帮我完善当前研究记录。')
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await expect(page.getByText('受控替身暂时失败')).toBeVisible()
    await page.getByRole('button', { name: '重试', exact: true }).click()
    await expect(page.locator('.artifact-card')).toBeVisible()
    await expect(page.locator('.artifact-card')).toContainText('研究记录建议')
    await page.locator('.artifact-card textarea').fill('人工修改后的研究记录建议。')
    const target = page.locator('.target-material select')
    await expect(target).toBeVisible()
    await target.selectOption({ index: 1 })
    await page.getByRole('button', { name: '保存为材料', exact: true }).click()
    await page.getByRole('alertdialog', { name: '确认 AI 草稿操作' }).getByRole('button', { name: '确认保存', exact: true }).click()
    await expect(page.getByText(/草稿已提交到材料/)).toBeVisible()
    expect(messageRequests).toBe(1)
    expect(savedPayload).toMatchObject({ content: '人工修改后的研究记录建议。', revision_note: '由全局 AI 对话保存为材料草稿' })
  })

  test('已配置真实 AI 服务时完成一次模型队列和流式冒烟', async ({ page }) => {
    test.setTimeout(90_000)
    await login(page, studentUsername, '/student/projects')
    const project = await projectByTitle(page, '核心闭环验收项目')
    const availability = await getJson<{ status: string }>(page, 'ai-availability/')
    test.skip(availability.status !== 'configured', `当前集成环境未配置真实 AI 服务（${availability.status}）`)
    await page.goto(`/student/ai?mode=research&projectId=${project.id}`)
    await expect(page.locator('.ai-workbench-composer__textarea')).toBeVisible()
    await page.locator('.ai-workbench-composer__textarea').fill('请用一句话总结当前项目的研究问题。')
    await page.getByRole('button', { name: '发送', exact: true }).click()
    await expect.poll(async () => {
      const assistant = page.locator('.message.assistant').last()
      return (await assistant.innerText()).replace('灵思 AI', '').trim()
    }, { timeout: 60_000, intervals: [1000, 2000] }).not.toMatch(/^正在排队|^正在生成|^$/)
    const logs = await getJson<Array<{ project: number; status: string }>>(page, `ai-logs/?project=${project.id}`)
    expect(logs.some((item) => item.project === project.id && ['completed', 'failed'].includes(item.status))).toBeTruthy()
  })
})
