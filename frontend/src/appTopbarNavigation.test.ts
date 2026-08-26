import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./components/AppTopbar.vue', import.meta.url), 'utf8')

describe('AppTopbar home navigation', () => {
  it('uses the platform route for platform administrators instead of the role key', () => {
    expect(source).toContain("role === 'platform_admin' ? '/platform/home'")
    expect(source).not.toContain('`/${auth.user.value.role}/home`')
  })
})

describe('AppTopbar notification center', () => {
  it('uses the personal notification feed and exposes the full notification center route', () => {
    expect(source).toContain('getNotifications')
    expect(source).toContain('markNotificationRead')
    expect(source).toContain('markAllNotificationsRead')
    expect(source).toContain("'/student/notifications'")
    expect(source).toContain("'/teacher/notifications'")
    expect(source).toContain('notifications:changed')
    expect(source).toContain('addEventListener')
    expect(source).not.toContain('getAnnouncements')
    expect(source).not.toContain('markAnnouncementRead')
  })

  it('keeps the popover compact and bounded to the shared notification list', () => {
    expect(source).toContain('personal.slice(0, 6)')
    expect(source).toContain('查看全部消息')
    expect(source).toContain('全部已读')
  })
})
