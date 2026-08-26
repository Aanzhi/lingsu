import { describe, expect, it } from 'vitest'

import { personalNotifications } from './notificationModel'

function notification(kind: string, id: number) {
  return {
    id,
    kind,
    title: `通知 ${id}`,
    body: '',
    link: '',
    is_read: false,
    created_at: '2026-08-27T10:00:00Z',
  }
}

describe('notification model', () => {
  it('keeps personal workflow events in the message center and leaves public notices to content resources', () => {
    const visible = personalNotifications([
      notification('material_revision_required', 1),
      notification('invitation_pending', 2),
      notification('school_announcement', 3),
      notification('platform_announcement', 4),
      notification('case_published', 5),
    ])

    expect(visible.map((item) => item.kind)).toEqual([
      'material_revision_required',
      'invitation_pending',
      'case_published',
    ])
  })
})
