import type { AppNotification } from '../api'

/**
 * 公告本身属于内容资源，不应在个人消息流中再次占据一条记录。
 * 保留后端通知数据不变，只在消息展示层划分个人事件与公共内容。
 */
export const PUBLIC_NOTIFICATION_KINDS = ['school_announcement', 'platform_announcement'] as const

const publicNotificationKinds = new Set<string>(PUBLIC_NOTIFICATION_KINDS)

export function isPublicNotification(item: Pick<AppNotification, 'kind'>) {
  return publicNotificationKinds.has(item.kind)
}

export function personalNotifications(items: AppNotification[]) {
  return items.filter((item) => !isPublicNotification(item))
}
