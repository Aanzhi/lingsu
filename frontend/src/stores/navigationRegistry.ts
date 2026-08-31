import { studentProjectsPath } from './pageContracts'

export type NavigationRole = 'student' | 'teacher' | 'platform_admin'
export type NavigationIcon = 'home' | 'projects' | 'journey' | 'review' | 'members' | 'content' | 'schools' | 'ai' | 'settings' | 'bell'

export interface NavigationItem {
  key: string
  label: string
  to: string
  icon: NavigationIcon
  children?: string[]
}

export interface NavigationChildItem {
  key: string
  label: string
  to: string
  icon: NavigationIcon
}

export interface StudentNavigationProject {
  id: number
  is_primary?: boolean
  is_archived?: boolean
  deleted_at?: string | null
}

const roleBasePath: Record<NavigationRole, string> = {
  student: '/student',
  teacher: '/teacher',
  platform_admin: '/platform',
}

/**
 * The project page promotes the primary project, or the first available
 * active project when an older account has not been assigned one yet. The
 * sidebar must use that same deterministic fallback or it will display a
 * current-project card while linking to the no-project query surfaces.
 */
export function resolveStudentNavigationProject(
  primaryProject: number | null | undefined,
  projects: StudentNavigationProject[] = [],
  contextProject: number | null | undefined = null,
): number | null {
  if (contextProject) return contextProject
  if (primaryProject) return primaryProject
  const activeProjects = projects.filter((project) => !project.is_archived && !project.deleted_at)
  return activeProjects.find((project) => project.is_primary)?.id ?? activeProjects[0]?.id ?? null
}

export function primaryNavigation(role: NavigationRole, primaryProject?: number | null): NavigationItem[] {
  if (role === 'student') return [
    ...studentProjectNavigation(primaryProject),
  ]
  if (role === 'teacher') return [
    { key: 'home', label: '工作台', to: '/teacher/home', icon: 'home' },
    { key: 'pool', label: '项目池', to: '/teacher/pool', icon: 'projects' },
    { key: 'projects', label: '指导项目', to: '/teacher/projects', icon: 'projects' },
    { key: 'ai', label: '灵思 AI', to: '/teacher/ai', icon: 'ai' },
    { key: 'reviews', label: '材料审核', to: '/teacher/reviews', icon: 'review' },
    { key: 'content', label: '公开内容', to: '/teacher/cases', icon: 'content', children: ['cases', 'competitions', 'announcements'] },
  ]
  return [
    { key: 'home', label: '平台概览', to: '/platform/home', icon: 'home' },
    { key: 'schools', label: '学校空间', to: '/platform/schools', icon: 'schools' },
    { key: 'ai-agents', label: 'Skills', to: '/platform/ai-agents', icon: 'ai' },
    { key: 'content', label: '赛事与公告', to: '/platform/competitions', icon: 'content', children: ['competitions', 'announcements', 'cases'] },
    { key: 'settings', label: '系统设置', to: '/platform/settings', icon: 'settings' },
  ]
}

function studentProjectNavigation(primaryProject?: number | null): NavigationItem[] {
  const projectBase = primaryProject ? `/student/projects/${primaryProject}` : null
  return [
    { key: 'home', label: '首页', to: '/student/home', icon: 'home' },
    { key: 'projects', label: '我的项目', to: '/student/projects', icon: 'projects' },
    { key: 'ai', label: '灵思 AI', to: '/student/ai', icon: 'ai' },
    { key: 'journey', label: '研究进程', to: projectBase ? `${projectBase}/map` : studentProjectsPath('journey'), icon: 'journey' },
    { key: 'invitations', label: '项目邀请', to: '/student/invitations', icon: 'members' },
    { key: 'cases', label: '案例库', to: '/student/cases', icon: 'content' },
    { key: 'competitions', label: '赛事信息', to: '/student/competitions', icon: 'content' },
    { key: 'announcements', label: '校内通知', to: '/student/announcements', icon: 'content' },
  ]
}

export function studentTopNavigation(primaryProject: number | null | undefined): NavigationChildItem[] {
  const projectBase = primaryProject ? `/student/projects/${primaryProject}` : '/student/projects'
  return [
    { key: 'home', label: '首页', to: '/student/home', icon: 'home' },
    { key: 'projects', label: '我的项目', to: '/student/projects', icon: 'projects' },
    { key: 'ai', label: '灵思 AI', to: '/student/ai', icon: 'ai' },
    { key: 'journey', label: '研究进程', to: primaryProject ? `${projectBase}/map` : studentProjectsPath('journey'), icon: 'journey' },
    { key: 'invitations', label: '项目邀请', to: '/student/invitations', icon: 'members' },
    { key: 'cases', label: '案例库', to: '/student/cases', icon: 'content' },
    { key: 'competitions', label: '赛事信息', to: '/student/competitions', icon: 'content' },
    { key: 'announcements', label: '校内通知', to: '/student/announcements', icon: 'content' },
  ]
}

/**
 * A section owns its detail routes as well as its index route. Keeping this
 * rule beside the registry prevents layouts from inventing slightly
 * different active-state rules and avoids adding duplicate detail entries to
 * the primary navigation.
 */
export function isNavigationActive(role: NavigationRole, item: NavigationItem, path: string, query: Record<string, unknown> = {}) {
  if (role === 'student') {
    if (item.key === 'projects') {
      const isProjectIndex = path === '/student/projects'
      const isFocusedSurface = ['journey', 'materials', 'apply'].includes(String(query.focus ?? ''))
      return /^\/student\/projects(?:\/\d+)?$/.test(path) && !(isProjectIndex && isFocusedSurface)
    }
    if (item.key === 'journey') {
      return /^\/student\/projects\/\d+\/(?:map|materials|tasks\/\d+)$/.test(path)
        || (path === '/student/projects' && ['journey', 'materials'].includes(String(query.focus ?? '')))
    }
  }
  const base = roleBasePath[role]
  const ownsNestedPath = path === item.to || path.startsWith(`${item.to}/`)
  const ownsChildPath = item.children?.some((child) => {
    const childPath = `${base}/${child}`
    return path === childPath || path.startsWith(`${childPath}/`)
  })
  return ownsNestedPath || Boolean(ownsChildPath)
}

const childLabels: Record<NavigationRole, Record<string, string>> = {
  student: { cases: '案例库', competitions: '赛事信息', announcements: '校内通知' },
  teacher: { cases: '案例库', competitions: '赛事信息', announcements: '学生公告' },
  platform_admin: { cases: '案例治理', competitions: '赛事管理', announcements: '系统公告' },
}

export function navigationChildren(role: NavigationRole, item: NavigationItem): NavigationChildItem[] {
  const base = roleBasePath[role]
  return (item.children ?? [])
    .filter((key) => childLabels[role][key])
    .map((key) => ({
      key,
      label: childLabels[role][key],
      to: `${base}/${key}`,
      icon: item.icon,
    }))
    // The parent is already the canonical entry for the first child route;
    // rendering both would put the same capability in the sidebar twice.
    .filter((child) => child.to !== item.to)
}

export function utilityNavigation(role: NavigationRole, primaryProject: number | null | undefined): NavigationChildItem[] {
  if (role === 'student') {
    return []
  }
  if (role === 'teacher') return [
    { key: 'members', label: '成员确认', to: '/teacher/members', icon: 'members' },
    { key: 'notifications', label: '工作通知', to: '/teacher/notifications', icon: 'bell' },
  ]
  return []
}
