export type PageRole = 'public' | 'student' | 'teacher' | 'platform' | 'console'

export type PageActionKind = 'route' | 'event' | 'submit' | 'download'

export interface PageActionContract {
  label: string
  target?: string
  kind: PageActionKind
}

export interface PageContract {
  key: string
  role: PageRole
  path: string
  title: string
  description: string | ((context: unknown) => string)
  primaryAction?: PageActionContract
  allowedQuery?: readonly string[]
}

export interface RouteLocationTarget {
  path: string
  query?: Record<string, string>
}

export type StudentProjectSurface = 'overview' | 'map' | 'materials' | 'report'
export type StudentProjectFocus = 'journey' | 'materials' | 'apply'

const studentProjectQuery = ['tab', 'create', 'focus'] as const

export const PAGE_CONTRACTS: PageContract[] = [
  { key: 'public.entry', role: 'public', path: '/', title: '灵溯', description: '了解学生、教师和学校如何在同一条科创项目工作流中协作。', primaryAction: { label: '登录工作台', target: '/login', kind: 'route' } },
  { key: 'public.login', role: 'public', path: '/login', title: '欢迎回到灵溯', description: '登录后进入与你身份匹配的工作台，继续处理项目或指导任务。', primaryAction: { label: '登录', kind: 'submit' } },
  { key: 'public.register', role: 'public', path: '/register', title: '创建工作台账号', description: '使用学校邀请码创建学生或教师账号，注册后直接进入对应工作台。', primaryAction: { label: '创建账号', kind: 'submit' }, allowedQuery: ['role'] },
  { key: 'public.platform-login', role: 'public', path: '/platform/login', title: '进入平台管理工作台', description: '平台管理员在这里管理学校空间、AI 模板、赛事公告和公开案例。', primaryAction: { label: '登录平台工作台', kind: 'submit' } },

  { key: 'student.home', role: 'student', path: '/student/home', title: '继续当前研究', description: '从当前项目的待办开始，查看进度、材料状态和下一项可完成任务。', primaryAction: { label: '开始任务', kind: 'route' } },
  { key: 'student.projects', role: 'student', path: '/student/projects', title: '我的项目', description: '查看项目进度，进入研究进程，管理已归档和回收站项目。', primaryAction: { label: '新建项目', kind: 'event' }, allowedQuery: studentProjectQuery },
  { key: 'student.project.map', role: 'student', path: '/student/projects/:id/map', title: '研究进程', description: '按章节推进任务，在具体任务中提交材料并查看审核意见。', primaryAction: { label: '继续当前任务', kind: 'route' } },
  { key: 'student.project.task', role: 'student', path: '/student/projects/:id/tasks/:taskId', title: '任务处理', description: '完成当前任务要求，补充证据后提交给指导教师审核。', primaryAction: { label: '提交材料', kind: 'submit' } },
  { key: 'student.project.report', role: 'student', path: '/student/projects/:id/report', title: '研究报告', description: '根据已通过材料查看报告结构，满足条件后导出 Word 或 PDF。' },
  { key: 'student.ai', role: 'student', path: '/student/ai', title: '灵思 AI', description: '围绕开题、研究推进和成果表达提供可核对的辅助建议。', primaryAction: { label: '发送问题', kind: 'submit' }, allowedQuery: ['mode', 'projectId', 'taskId', 'agent', 'researchQuestion'] },
  { key: 'student.notifications', role: 'student', path: '/student/notifications', title: '消息中心', description: '查看与你有关的审核结果、项目邀请、成员变化和成果状态；平台公告与学校通知请到内容资源查看。' },
  { key: 'student.invitations', role: 'student', path: '/student/invitations', title: '项目邀请', description: '处理同学或教师发来的项目邀请；新邀请从具体项目的成员区域发起。' },
  { key: 'student.public-applications', role: 'student', path: '/student/public-applications', title: '公开成果申请', description: '查看校内展示申请和教师发起的全平台展示邀请，确认公开材料范围后再提交。', allowedQuery: ['projectId'] },
  { key: 'student.cases', role: 'student', path: '/student/cases', title: '案例库', description: '浏览已公开的学生项目案例，按研究方向参考过程和成果。' },
  { key: 'student.competitions', role: 'student', path: '/student/competitions', title: '赛事信息', description: '查看平台发布的赛事和截止时间，判断当前项目是否适合参加。' },
  { key: 'student.announcements', role: 'student', path: '/student/announcements', title: '平台公告', description: '浏览平台发布的公告和学校公开通知；需要处理的个人事项请进入消息中心。' },

  { key: 'teacher.home', role: 'teacher', path: '/teacher/home', title: '指导工作台', description: '查看本校项目、待审核材料和成员事项，优先处理需要你决定的记录。', primaryAction: { label: '查看待审核材料', target: '/teacher/reviews', kind: 'route' } },
  { key: 'teacher.pool', role: 'teacher', path: '/teacher/pool', title: '项目池', description: '浏览本校尚未认领的项目，先查看开题内容，再确认是否认领为指导项目。', primaryAction: { label: '查看开题报告', kind: 'event' } },
  { key: 'teacher.projects', role: 'teacher', path: '/teacher/projects', title: '指导项目', description: '查看已认领、已归档和回收站项目，进入详情继续指导。' },
  { key: 'teacher.ai', role: 'teacher', path: '/teacher/ai', title: '灵思 AI 指导室', description: '围绕本人负责项目诊断风险、准备指导问题，并形成需要人工确认的指导建议。', primaryAction: { label: '发送指导问题', kind: 'submit' }, allowedQuery: ['mode', 'projectId', 'agent'] },
  { key: 'teacher.project', role: 'teacher', path: '/teacher/projects/:id', title: '指导项目详情', description: '跟进项目研究章节、材料审核和成员状态。', primaryAction: { label: '查看待审核材料', kind: 'route' } },
  { key: 'teacher.project-template', role: 'teacher', path: '/teacher/projects/:id/template', title: '配置材料范本', description: '维护本项目的材料提交说明和参考范本，学生会在任务页看到更新。' },
  { key: 'teacher.reviews', role: 'teacher', path: '/teacher/reviews', title: '材料审核', description: '按提交顺序处理负责项目的材料，给出通过或明确的修改建议。', primaryAction: { label: '打开审核详情', kind: 'route' }, allowedQuery: ['projectId'] },
  { key: 'teacher.review', role: 'teacher', path: '/teacher/reviews/:submissionId', title: '审核详情', description: '核对正文、附件和真实性确认后，提交审核决定。', primaryAction: { label: '提交审核决定', kind: 'submit' }, allowedQuery: ['projectId'] },
  { key: 'teacher.members', role: 'teacher', path: '/teacher/members', title: '成员与邀请', description: '确认成员加入申请，并从具体指导项目发出成员邀请。', primaryAction: { label: '邀请成员', kind: 'event' }, allowedQuery: ['projectId'] },
  { key: 'teacher.notifications', role: 'teacher', path: '/teacher/notifications', title: '教师通知中心', description: '查看与你负责项目有关的审核、项目池和成员动态；学校公告请到内容资源查看。' },
  { key: 'teacher.cases', role: 'teacher', path: '/teacher/cases', title: '案例库', description: '浏览已公开案例，为指导和选题提供参考。' },
  { key: 'teacher.competitions', role: 'teacher', path: '/teacher/competitions', title: '赛事信息', description: '查看平台赛事信息，为学生提供参赛建议。' },
  { key: 'teacher.announcements', role: 'teacher', path: '/teacher/announcements', title: '学生通知公告', description: '面向本校学生发布研究、活动和项目相关通知。', primaryAction: { label: '创建公告', kind: 'event' } },

  { key: 'platform.home', role: 'platform', path: '/platform/home', title: '平台概览', description: '查看学校授权、项目活跃度和服务状态，具体管理操作进入对应工作页。', primaryAction: { label: '查看学校空间', target: '/platform/schools', kind: 'route' } },
  { key: 'platform.schools', role: 'platform', path: '/platform/schools', title: '学校空间', description: '管理学校空间和授权状态；进入详情查看数据，开关只控制授权。', primaryAction: { label: '添加学校', kind: 'event' } },
  { key: 'platform.school', role: 'platform', path: '/platform/schools/:id', title: '学校详情', description: '查看该学校的成员、项目、邀请码和服务配额。' },
  { key: 'platform.ai-agents', role: 'platform', path: '/platform/ai-agents', title: 'AI 助手模板', description: '维护师生端可用的 AI 模板、角色、分组、上下文范围和启用状态。', primaryAction: { label: '新建模板', kind: 'event' } },
  { key: 'platform.competitions', role: 'platform', path: '/platform/competitions', title: '赛事管理', description: '创建、发布或撤回面向师生的赛事信息。', primaryAction: { label: '发布赛事', kind: 'event' } },
  { key: 'platform.announcements', role: 'platform', path: '/platform/announcements', title: '系统公告', description: '发布平台公告，并让学校端在通知中心查看。', primaryAction: { label: '发布公告', kind: 'event' } },
  { key: 'platform.cases', role: 'platform', path: '/platform/cases', title: '案例治理', description: '审核学生公开成果申请，决定发布、下架或恢复。' },
  { key: 'platform.settings', role: 'platform', path: '/platform/settings', title: '系统设置', description: '查看安全策略和服务健康状态，低频配置不进入日常运营页。' },

  { key: 'console.overview', role: 'console', path: '#overview', title: '运行概览', description: '查看本机服务状态，按需启停项目资源、执行健康验收和读取日志。' },
  { key: 'console.checks', role: 'console', path: '#checks', title: '健康验收', description: '执行项目健康检查，确认服务和真实登录流程可用。' },
  { key: 'console.services', role: 'console', path: '#services', title: '服务明细', description: '查看 Docker 服务状态，并单独控制后端服务栈。' },
  { key: 'console.logs', role: 'console', path: '#logs', title: '运行日志', description: '选择服务并读取最近日志，定位启动和运行问题。' },
]

export function pageContract(key: string) {
  return PAGE_CONTRACTS.find((contract) => contract.key === key)
}

export function pageDescription(key: string, context?: unknown) {
  const contract = pageContract(key)
  if (!contract) return ''
  return typeof contract.description === 'function' ? contract.description(context) : contract.description
}

export function studentProjectRoute(id: number | string, surface: StudentProjectSurface = 'map') {
  const base = `/student/projects/${id}`
  if (surface === 'overview' || surface === 'map' || surface === 'materials') return `${base}/map`
  if (surface === 'report') return `${base}/report`
  return `${base}/map`
}

export function studentTaskRoute(projectId: number | string, taskId: number | string) {
  return `/student/projects/${projectId}/tasks/${taskId}`
}

export function studentProjectsLocation(focus?: StudentProjectFocus): RouteLocationTarget {
  return focus ? { path: '/student/projects', query: { focus: focus === 'materials' ? 'journey' : focus } } : { path: '/student/projects' }
}

export function studentProjectsPath(focus?: StudentProjectFocus) {
  return focus ? `/student/projects?focus=${focus === 'materials' ? 'journey' : focus}` : '/student/projects'
}

export function teacherReviewRoute(submissionId?: number | string, projectId?: number | string): string | RouteLocationTarget {
  const path = submissionId === undefined ? '/teacher/reviews' : `/teacher/reviews/${submissionId}`
  return projectId === undefined ? path : { path, query: { projectId: String(projectId) } }
}

export function teacherMembersRoute(projectId?: number | string): string | RouteLocationTarget {
  return projectId === undefined ? '/teacher/members' : { path: '/teacher/members', query: { projectId: String(projectId) } }
}

export function platformSchoolRoute(id: number | string) {
  return `/platform/schools/${id}`
}

export function consoleSectionLocations() {
  return PAGE_CONTRACTS.filter((contract) => contract.role === 'console').map((contract) => contract.path)
}
