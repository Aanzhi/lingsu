import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { routeRecords } from './router'

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), 'utf8')
}

describe('route-reused page lifecycle contracts', () => {
  it('reloads project surfaces and stops report polling when the route changes', () => {
    const page = source('./pages/student/StudentProject.vue')
    expect(page).toContain('onBeforeUnmount')
    expect(page).toContain('watch([projectId, surface]')
    expect(page).toContain('window.clearTimeout(pollTimer)')
  })

  it('reloads the task data when moving between tasks without remounting', () => {
    const page = source('./pages/student/StudentTask.vue')
    expect(page).toContain('watch([projectId, taskId]')
    expect(page).toContain('async function load()')
  })

  it('resets scoped filters and dialogs when shared pages change surface or entity', () => {
    const library = source('./pages/shared/ContentLibrary.vue')
    const school = source('./pages/platform/SchoolDetail.vue')
    const teacher = source('./pages/teacher/TeacherWorkbench.vue')
    const platform = source('./pages/platform/PlatformConsole.vue')

    expect(library).toContain('watch([surface, view, () => String(route.query.projectId ?? \'\')], () =>')
    expect(library).toContain("keyword.value = ''")
    expect(school).toContain('watch(schoolId, () =>')
    const student = routeRecords.find((route) => route.path === '/student')!
    expect(typeof student.children?.find((route) => route.path === 'public-applications')?.redirect).toBe('function')
    expect(teacher).toContain('watch([surface, () => route.params.submissionId]')
    expect(platform).toContain('watch(surface, () =>')
    expect(platform).toContain('dataReady.value = true')

    const settings = source('./pages/platform/PlatformSettings.vue')
    expect(settings).toContain('loading.value = true')
    expect(settings).toContain('v-if="loading"')
  })
})
