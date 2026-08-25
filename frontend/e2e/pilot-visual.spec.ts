import { expect, test, type Page } from '@playwright/test'
import { login, seedCoreFlow } from './realAuth'

const outputDir = 'artifacts/ui-pilot'

test.beforeAll(seedCoreFlow)

async function loginAndWait(page: Page, role: 'student' | 'teacher' | 'platform_admin', destination: string) {
  await login(page, role, destination)
  await expect(page.locator('.page').first()).toBeVisible()
  await page.locator('.loading-state').waitFor({ state: 'hidden', timeout: 15_000 }).catch(() => undefined)
}

async function capture(page: Page, name: string) {
  await page.evaluate(() => scrollTo(0, 0))
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy()
  await page.screenshot({ path: `${outputDir}/${name}.png`, fullPage: true, animations: 'disabled' })
}

async function selectDemoRole(page: Page, role: 'student' | 'teacher' | 'platform') {
  await page.evaluate((nextRole) => {
    const trigger = document.createElement('button')
    trigger.dataset.role = nextRole
    document.body.appendChild(trigger)
    trigger.click()
    trigger.remove()
  }, role)
}

test('五个样板页在 1280 与 1440 下保持方案 B 几何并生成截图矩阵', async ({ page }) => {
  test.setTimeout(120_000)
  const viewports = [{ width: 1280, height: 900 }, { width: 1440, height: 960 }]
  const references = ['student', 'teacher', 'platform'] as const

  for (const viewport of viewports) {
    await page.setViewportSize(viewport)

    for (const key of references) {
      await page.goto('/design-demo.html')
      await selectDemoRole(page, key)
      await expect(page.locator('#nav-label')).toHaveText(key === 'student' ? '学生空间' : key === 'teacher' ? '指导空间' : '平台空间')
      await capture(page, `${viewport.width}-reference-${key}`)
    }

    await page.context().clearCookies()
    await page.goto('/')
    await capture(page, `${viewport.width}-public`)

    await page.context().clearCookies()
    await loginAndWait(page, 'student', '/student/home')
    await expect(page.locator('.workspace-shell--hero')).toHaveCount(1)
    await expect(page.locator('aside.workspace-sidebar')).toHaveCount(0)
    await expect(page.getByRole('link', { name: '进入工作台', exact: true })).toBeVisible()
    await capture(page, `${viewport.width}-student`)

    await page.context().clearCookies()
    await loginAndWait(page, 'teacher', '/teacher/home')
    await expect(page.locator('.workspace-shell--hero')).toHaveCount(1)
    await expect(page.locator('aside.workspace-sidebar')).toHaveCount(0)
    await expect(page.getByRole('link', { name: '进入工作台', exact: true })).toBeVisible()
    await capture(page, `${viewport.width}-teacher`)

    await page.context().clearCookies()
    await loginAndWait(page, 'platform_admin', '/platform/home')
    await expect(page.locator('.workspace-shell--hero')).toHaveCount(0)
    await expect(page.locator('aside.workspace-sidebar')).toHaveCount(1)
    await capture(page, `${viewport.width}-platform`)

    await page.goto('http://127.0.0.1:8800/')
    await expect(page.getByRole('heading', { name: '灵溯 · 项目控制台' })).toBeVisible()
    await expect(page.locator('#console-state')).toContainText('宿主机独立运行', { timeout: 15_000 })
    for (const hash of ['#overview', '#checks', '#services', '#logs']) {
      await page.goto(`http://127.0.0.1:8800/${hash}`)
      const anchorState = await page.locator(hash).evaluate((element) => ({
        active: document.querySelector('.console-sidebar a.active')?.getAttribute('href'),
        top: element.getBoundingClientRect().top,
        topbarBottom: document.querySelector('.console-topbar')?.getBoundingClientRect().bottom ?? 0,
      }))
      expect(anchorState.active).toBe(hash)
      expect(anchorState.top).toBeGreaterThanOrEqual(anchorState.topbarBottom)
    }
    await page.goto('http://127.0.0.1:8800/')
    await capture(page, `${viewport.width}-console`)
  }
})
