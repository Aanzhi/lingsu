export interface ManagementPoolProject {
  id: number
  title: string
  problem: string
  studentName: string
  primaryTeacherId: number | null
  status: 'unclaimed' | 'claimed'
}

export interface ManagementSchool {
  id: number
  name: string
  isAuthorized: boolean
  projectCount: number
  activeProjectCount: number
  studentCount: number
  teacherCount: number
}

export interface ManagementAgent {
  key: string
  name: string
  category: string
  isActive: boolean
}

export interface ManagementCase {
  id: number
  projectTitle: string
  teacherInvite: boolean
  studentConsent: boolean
  platformReview: boolean
}

export interface ManagementFixture {
  currentTeacherId: number
  poolProjects: ManagementPoolProject[]
  schools: ManagementSchool[]
  agents: ManagementAgent[]
  cases: ManagementCase[]
  teacherNotifications: Array<{ id: number; title: string; body: string; isRead: boolean }>
}

export const managementFixture: ManagementFixture = {
  currentTeacherId: 12,
  poolProjects: [
    { id: 501, title: '校园雨水回收观察', problem: '不同收集方式会如何影响雨水再利用？', studentName: '李同学', primaryTeacherId: null, status: 'unclaimed' },
    { id: 502, title: '午间光照与植物生长', problem: '午间光照时长是否影响薄荷的叶片数量？', studentName: '王同学', primaryTeacherId: 11, status: 'claimed' },
    { id: 503, title: '校园河流微塑料调查', problem: '校园河流不同位置的微塑料来源是否存在差异？', studentName: '陈同学', primaryTeacherId: 12, status: 'claimed' },
  ],
  schools: [
    { id: 3, name: '东川实验学校', isAuthorized: true, projectCount: 12, activeProjectCount: 8, studentCount: 86, teacherCount: 6 },
    { id: 4, name: '南岭外国语学校', isAuthorized: false, projectCount: 7, activeProjectCount: 0, studentCount: 45, teacherCount: 4 },
  ],
  agents: [
    { key: 'opening-topic', name: '研究问题助手', category: '开题', isActive: true },
    { key: 'defense-prep', name: '成果表达问答准备', category: '成果表达', isActive: false },
  ],
  cases: [
    { id: 801, projectTitle: '午间光照与植物生长', teacherInvite: true, studentConsent: false, platformReview: false },
    { id: 802, projectTitle: '校园雨水回收观察', teacherInvite: true, studentConsent: true, platformReview: false },
  ],
  teacherNotifications: [
    { id: 901, title: '有新的项目进入项目池', body: '校园雨水回收观察等待教师认领。', isRead: false },
    { id: 902, title: '学生补交了实验日志', body: '校园河流微塑料调查有新的材料版本。', isRead: true },
  ],
}
