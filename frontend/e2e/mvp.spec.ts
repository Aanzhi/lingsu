import { expect, test, type Page } from '@playwright/test'

async function login(page: Page, role: 'student' | 'teacher' | 'platform_admin', destination: string) {
  await page.goto('/login')
  const result = await page.evaluate(async (requestedRole) => {
    const response = await fetch('/api/demo-login/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ role: requestedRole }),
    })
    return { ok: response.ok, status: response.status }
  }, role)
  expect(result.ok, `demo login failed with ${result.status}`).toBeTruthy()
  await page.goto(destination)
}

test('学生可以进入项目和 AI 工作台', async ({ page }) => {
  await login(page, 'student', '/student/projects')
  await expect(page.getByRole('heading', { name: '项目书架' })).toBeVisible()
  await page.goto('/student/ai')
  await expect(page.getByText('全局 AI 工作台')).toBeVisible()
  await expect(page.getByRole('button', { name: '＋ 新建对话' })).toBeVisible()
})

test('教师和平台管理员分别进入各自工作台', async ({ page }) => {
  await login(page, 'teacher', '/teacher/reviews')
  await expect(page.getByRole('heading', { name: '学生材料审核' })).toBeVisible()

  await page.context().clearCookies()
  await login(page, 'platform_admin', '/platform/competitions')
  await expect(page.getByRole('heading', { name: '赛事管理' })).toBeVisible()
})
