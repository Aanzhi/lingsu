import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')

describe('progressive first paint contracts', () => {
  it('mounts the application before route bootstrap finishes', () => {
    const main = read('./main.ts')
    const mountIndex = main.indexOf("app.mount('#app')")
    expect(mountIndex).toBeGreaterThanOrEqual(0)
    expect(main).not.toContain("router.isReady().then(() => app.mount('#app'))")
    expect(read('./App.vue')).toContain('router.isReady()')
  })

  it('keeps a neutral shell visible while authentication is restoring', () => {
    const app = read('./App.vue')
    expect(app).toContain('app-bootstrap-shell')
    expect(app).toContain('正在打开灵溯')
  })

  it('does not hide the student home body behind the first request', () => {
    const home = read('./pages/student/StudentHome.vue')
    expect(home).toContain('student-home-skeleton')
    expect(home).not.toContain('<div v-if="loading" class="loading-state"')
    expect(home).toContain('<template v-else>')
  })

  it('keeps the project progress structure visible while project data is loading', () => {
    const project = read('./pages/student/StudentProject.vue')
    expect(project).toContain('project-detail-skeleton')
    expect(project).not.toContain('project && !loading')
  })

  it('keeps the task workspace frame visible while task data is loading', () => {
    const task = read('./pages/student/StudentTask.vue')
    expect(task).toContain('task-page-skeleton')
    expect(task).not.toContain('task && project && material && !dataLoading')
  })

  it('renders the AI workbench frame before projects, agents, and conversations finish', () => {
    const ai = read('./pages/shared/AICenter.vue')
    expect(ai).toContain('class="page ai-center-page ai-workbench-frame"')
    expect(ai).toContain('ai-workbench-skeleton')
    expect(ai).toContain('aria-label="正在准备灵思 AI"')
    expect(ai).not.toContain('v-if="!loading && !hasConversationMessages"')
  })

  it('splits initial projects from background student resources', () => {
    const student = read('./stores/student.ts')
    expect(student).toContain('loadProjects')
    expect(student).toContain('loadBackgroundResources')
    expect(student).not.toContain('getProjects(), getProjectTasks(), getMaterials(), getCompetitions(), getAnnouncements()')
  })

  it('separates personal messages from public content labels', () => {
    const navigation = read('./stores/navigationRegistry.ts')
    const content = read('./pages/shared/ContentLibrary.vue')
    const notifications = read('./components/NotificationCenter.vue')
    expect(navigation).toContain("key: 'notifications', label: '工作通知'")
    expect(navigation).toContain("key: 'content', label: '公开内容'")
    expect(navigation).toContain("announcements: '平台公告'")
    expect(content).toContain('平台公告')
    expect(content).toContain('需要处理的个人事项请进入工作通知')
    expect(notifications).toContain('personalNotifications')
    expect(notifications).toContain('项目工作流动态')
  })

  it('renders the supervising teacher display name when the project API provides it', () => {
    const api = read('./api.ts')
    const project = read('./pages/student/StudentProject.vue')
    const serializer = read('../../backend/apps/core/serializers.py')
    expect(api).toContain('primary_teacher_name: string | null')
    expect(serializer).toContain('primary_teacher_name')
    expect(project).toContain('project.primary_teacher_name')
  })
})
