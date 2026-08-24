export const PORTAL_FIXTURE_DATE = '2026-08-25T00:00:00.000Z'

export interface StudentFixtureProject {
  id: number
  title: string
  status: 'unclaimed' | 'active' | 'completed' | 'archived' | 'trashed'
  problem: string
  progress: number
  trashedAt?: string
}

export interface StudentFixtureTaskMaterial {
  kind: 'standard' | 'experiment_log'
  completed: boolean
}

export interface StudentFixtureTask {
  id: number
  projectId: number
  title: string
  status: string
  requiredMaterials: StudentFixtureTaskMaterial[]
  feedback?: string
}

export interface StudentFixtureNotification {
  id: number
  kind: string
  title: string
  body: string
  isRead: boolean
  link?: string
}

export interface StudentFixture {
  school: { id: number; name: string }
  currentProjectId: number | null
  projects: StudentFixtureProject[]
  tasks: StudentFixtureTask[]
  notifications: StudentFixtureNotification[]
  materials: Array<{ id: number; projectId: number; title: string; content: string; status: string }>
  invitations: Array<{ id: number; projectTitle: string; inviter: string; status: 'pending' | 'accepted' | 'rejected' }>
  publicCases: Array<{ id: number; projectTitle: string; status: 'draft' | 'pending_teacher' | 'published'; scope: 'school' | 'platform' }>
}

export const studentFixture: StudentFixture = {
  school: { id: 3, name: '东川实验学校' },
  currentProjectId: 8,
  projects: [
    { id: 8, title: '校园积水的可持续观察', status: 'active', problem: '不同坡度会如何影响校园积水的持续时间？', progress: 42 },
    { id: 9, title: '午间光照与植物生长', status: 'completed', problem: '午间光照时长是否影响薄荷的叶片数量？', progress: 100 },
    { id: 10, title: '旧衣再生材料实验', status: 'archived', problem: '不同纤维配比的再生材料强度有什么差异？', progress: 100 },
    { id: 11, title: '待清理的风向观察', status: 'trashed', problem: '校园不同区域的风向是否存在稳定差异？', progress: 18, trashedAt: '2026-08-10T00:00:00.000Z' },
    { id: 12, title: '待认领的校园声音地图', status: 'unclaimed', problem: '校园不同区域的声音来源如何分类？', progress: 0 },
  ],
  tasks: [
    { id: 801, projectId: 8, title: '把观察写成研究问题', status: 'approved', requiredMaterials: [{ kind: 'standard', completed: true }] },
    { id: 802, projectId: 8, title: '设计一次校园积水实验', status: 'in_progress', requiredMaterials: [{ kind: 'standard', completed: false }, { kind: 'experiment_log', completed: false }], feedback: '请补充实验日志中的观察时间和现场条件。' },
    { id: 803, projectId: 8, title: '整理实验结果', status: 'available', requiredMaterials: [{ kind: 'standard', completed: false }] },
    { id: 901, projectId: 9, title: '完成项目报告', status: 'completed', requiredMaterials: [{ kind: 'standard', completed: true }] },
  ],
  notifications: [
    { id: 1, kind: 'review', title: '教师留下了修改建议', body: '实验日志还需要补充观察条件。', isRead: false, link: '/student/projects/8/tasks/802' },
    { id: 2, kind: 'school', title: '本周科创分享会报名开始', body: '学校将在周五举行校内项目分享会。', isRead: false, link: '/student/announcements' },
    { id: 3, kind: 'system', title: '项目已归档', body: '旧衣再生材料实验已保留在项目档案中。', isRead: true, link: '/student/projects?tab=archived' },
  ],
  materials: [
    { id: 81, projectId: 8, title: '研究问题说明', content: '不同坡度会如何影响校园积水的持续时间？', status: 'approved' },
    { id: 82, projectId: 8, title: '实验日志', content: '', status: 'draft' },
    { id: 91, projectId: 9, title: '项目报告', content: '已完成的观察与分析。', status: 'approved' },
  ],
  invitations: [{ id: 301, projectTitle: '校园昆虫观察', inviter: '林老师', status: 'pending' }],
  publicCases: [{ id: 401, projectTitle: '午间光照与植物生长', status: 'published', scope: 'school' }],
}
