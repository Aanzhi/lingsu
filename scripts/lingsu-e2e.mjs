// 端到端登录验证：playwright + headless chromium 跑真实浏览器登录流程
// 成功：stdout 单行 {"ok":true,...}
// 失败：stdout 单行 {"ok":false,"error":"...","step":"...","details":{...}}
// 在控制台 `project-console.py` 里用 subprocess 触发，结果 JSON 写到 stdout。
import { createRequire } from 'node:module'

const require = createRequire(new URL('../frontend/package.json', import.meta.url))
const { chromium } = require('playwright')

const FRONTEND_URL = process.env.LS_FRONTEND_URL || 'http://127.0.0.1:5173/login'
const USERNAME = process.env.LS_E2E_USER || 'demo-student'
const PASSWORD = process.env.LS_E2E_PASS || 'lingsu-demo-2026'

function emit(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n')
}

const browser = await chromium.launch({ headless: true })
const ctx = await browser.newContext({ ignoreHTTPSErrors: true })
const page = await ctx.newPage()

const consoleErrors = []
const failedRequests = []
page.on('console', (m) => {
  if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200))
})
page.on('requestfailed', (req) => {
  failedRequests.push({ url: req.url(), failure: req.failure()?.errorText || 'unknown' })
})

let loginReqHeaders = null
let loginResponse = null
page.on('request', (req) => {
  if (/\/login\//.test(req.url()) && req.method() === 'POST') {
    req.allHeaders().then((h) => { loginReqHeaders = h })
  }
})
page.on('response', async (res) => {
  if (/\/login\//.test(res.url()) && res.request().method() === 'POST') {
    loginResponse = { status: res.status(), body: (await res.text()).slice(0, 400) }
  }
})

try {
  await page.goto(FRONTEND_URL, { waitUntil: 'networkidle', timeout: 20000 })
} catch (e) {
  await browser.close()
  emit({ ok: false, step: 'goto_frontend', error: String(e), consoleErrors, failedRequests })
  process.exit(0)
}

try {
  await page.locator('.demo-hint__chip').first().click({ timeout: 5000 })
} catch {
  await page.fill('input[autocomplete="username"]', USERNAME)
  await page.fill('input[autocomplete="current-password"]', PASSWORD)
}

try {
  await page.click('button[type="submit"].primary-button', { timeout: 5000 })
} catch (e) {
  await browser.close()
  emit({ ok: false, step: 'click_login', error: String(e), consoleErrors, failedRequests })
  process.exit(0)
}

await page.waitForTimeout(3000)
const finalUrl = page.url()
const errMsg = await page.locator('.form-error').first().textContent().catch(() => null)

await browser.close()

const result = {
  ok: finalUrl.includes('/home') && !errMsg,
  finalUrl,
  errorText: errMsg,
  loginStatus: loginResponse?.status ?? null,
  csrfTokenSent: !!(loginReqHeaders?.['x-csrftoken'] || loginReqHeaders?.['X-CSRFToken']),
  consoleErrors,
  failedRequests,
  ts: Math.floor(Date.now() / 1000),
}
emit(result)
