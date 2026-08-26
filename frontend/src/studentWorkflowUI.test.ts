import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

import { routeRecords } from './router'
import { studentProjectRoute, studentTaskRoute } from './stores/pageContracts'
import { primaryNavigation } from './stores/navigationRegistry'

const read = (path: string) => readFileSync(new URL(path, import.meta.url), 'utf8')

describe('student project workflow UI contracts', () => {
  it('opens a project directly in research progress and keeps material URLs as compatibility redirects', () => {
    expect(studentProjectRoute(91)).toBe('/student/projects/91/map')
    expect(studentProjectRoute(91, 'materials')).toBe('/student/projects/91/map')
    expect(studentTaskRoute(91, 500)).toBe('/student/projects/91/tasks/500')

    const student = routeRecords.find((route) => route.path === '/student')!
    const overview = student.children?.find((route) => route.path === 'projects/:id')
    const materials = student.children?.find((route) => route.path === 'projects/:id/materials')
    expect(typeof overview?.redirect).toBe('function')
    expect(typeof materials?.redirect).toBe('function')
  })

  it('keeps the research progress page as the single task and material surface', () => {
    const project = read('./pages/student/StudentProject.vue')
    expect(project).toContain('class="demo-chapter-accordion paper-card"')
    expect(project).toContain("studentProjectRoute(project.id, 'report')")
    expect(project).toContain('研究报告')
    expect(project).not.toContain('材料记录')
    expect(project).not.toContain('project-progress-tabs')
    expect(project).not.toContain('view === \'materials\'')
  })

  it('paginates the project shelf instead of rendering the entire collection', () => {
    const projects = read('./pages/student/StudentProjects.vue')
    expect(projects).toContain('const PROJECTS_PAGE_SIZE = 6')
    expect(projects).toContain('const visibleProjects = computed')
    expect(projects).toContain('class="project-pagination"')
    expect(projects).toContain('class="student-project-grid"')
    expect(projects).toContain('v-for="project in visibleProjects"')
    expect(projects).not.toContain('class="project-card-grid"')
  })

  it('gives the active project a featured surface and keeps the remaining shelf paginated', () => {
    const projects = read('./pages/student/StudentProjects.vue')
    expect(projects).toContain('const featuredProject = computed')
    expect(projects).toContain('class="current-project-panel paper-card"')
    expect(projects).toContain('class="current-project-panel__identity"')
    expect(projects).toContain('class="current-project-panel__content"')
    expect(projects).toContain('class="current-project-panel__facts"')
    expect(projects).toContain('class="current-project-panel__actions"')
    expect(projects).toContain('class="student-project-grid"')
    expect(projects).toContain('class="student-project-card"')
    expect(projects).toContain('primary_teacher_name')
    expect(projects).toContain('其他项目')
    expect(projects).toContain('const PROJECTS_PAGE_SIZE = 6')
    expect(projects).not.toContain('class="project-list-item"')
  })

  it('uses arrow navigation for agents without a visible horizontal scrollbar', () => {
    const modeTabs = read('./components/ai/AIModeTabs.vue')
    expect(modeTabs).toContain('ai-agent-arrow')
    expect(modeTabs).toContain('visibleAgents')
    expect(modeTabs).not.toContain('overflow-x: auto')
  })

  it('exposes student content pages from the sidebar and makes the picker wide enough for grouped tools', () => {
    const student = primaryNavigation('student')
    expect(student.find((item) => item.key === 'content')?.children).toEqual(['cases', 'competitions', 'announcements'])
    expect(read('./components/ai/AIToolPicker.vue')).toContain('agent-menu--wide')
  })

  it('gives the task editor a structured main column and sticky context column', () => {
    const task = read('./pages/student/StudentTask.vue')
    expect(task).toContain('task-main-column')
    expect(task).toContain('task-context-column')
    expect(task).toContain('position: sticky')
  })

  it('separates task requirements, response editing, and support context', () => {
    const task = read('./pages/student/StudentTask.vue')
    expect(task).toContain('class="task-brief paper-card"')
    expect(task).toContain('class="task-response-card')
    expect(task).toContain('class="task-support-column')
    expect(task).toContain('class="task-attachment-panel"')
    expect(task).toContain('aria-label="我的记录"')
    expect(task).not.toContain('class="demo-task-main task-main-column paper-card"')
  })
})
