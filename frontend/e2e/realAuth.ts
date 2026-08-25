import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'

import { expect, type Page } from '@playwright/test'

const repoRoot = process.cwd().endsWith('/frontend') ? resolve(process.cwd(), '..') : process.cwd()
const password = 'core-e2e-pass-2026'

export type RealRole = 'student' | 'teacher' | 'platform_admin'

const usernames: Record<RealRole, string> = {
  student: 'core-e2e-student',
  teacher: 'core-e2e-teacher',
  platform_admin: 'core-e2e-platform',
}

export function seedCoreFlow() {
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

export async function login(page: Page, role: RealRole, destination: string) {
  await page.context().clearCookies()
  await page.goto('/login')
  const username = usernames[role]
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
