import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

function source(path: string) {
  return readFileSync(new URL(path, import.meta.url), 'utf8')
}

describe('page copy and entry contracts', () => {
  it('uses task-specific student copy instead of the Demo B slogan', () => {
    const home = source('./pages/student/StudentHome.vue')
    const projects = source('./pages/student/StudentProjects.vue')
    const invitations = source('./pages/student/StudentInvitations.vue')

    expect(home).toContain('继续当前研究')
    expect(home).toContain('从当前项目的待办开始，查看进度、材料状态和下一项可完成任务。')
    expect(projects).toContain('查看项目进度，进入研究进程，管理已归档和回收站项目。')
    expect(invitations).toContain('处理同学或教师发来的项目邀请；新邀请从具体项目的成员区域发起。')
    expect(home).not.toContain('研究不是一次完成的答案，而是从一个好问题开始。这里会告诉你今天最重要的下一步。')
    expect(projects).not.toContain('一个项目就是一条研究旅程。进入项目后，只保留与你当前阶段有关的信息。')
    expect(invitations).not.toContain('邀请统一从通知中心进入，不额外占用项目主导航。')
  })

  it('keeps public entry links and role pages on real destinations', () => {
    const entry = source('./pages/public/EntryPage.vue')
    const register = source('./pages/public/RegisterPage.vue')
    const platformLogin = source('./pages/public/PlatformLoginPage.vue')
    const notifications = source('./components/NotificationCenter.vue')

    expect(entry).toContain('id="platform"')
    expect(entry).not.toContain('to="/login">查看平台介绍</')
    expect(register).toContain('route.query.role')
    expect(register).not.toContain('role-segment')
    expect(platformLogin.match(/to="\/login"/g)?.length ?? 0).toBe(1)
    expect(notifications).toContain("title: '消息'")
    expect(notifications).toContain('审核结果、项目邀请、成员变化和成果状态')
    expect(notifications).not.toContain('平台公告与学校通知请到内容资源查看')
  })

  it('does not keep known no-op or duplicate page controls', () => {
    const home = source('./pages/student/StudentHome.vue')
    const teacherWorkbench = source('./pages/teacher/TeacherWorkbench.vue')
    const teacherDetail = source('./pages/teacher/TeacherProjectDetail.vue')
    const teacherTemplate = source('./pages/teacher/TeacherProjectTemplate.vue')
    const content = source('./pages/shared/ContentLibrary.vue')
    const platform = source('./pages/platform/PlatformConsole.vue')
    const settings = source('./pages/platform/PlatformSettings.vue')

    expect(home).not.toContain('打开研究旅程 →')
    expect(teacherWorkbench).not.toContain('v-else-if="surface === \'projects\'" class="secondary-button"')
    expect(teacherWorkbench).not.toContain('type="button">查看成员</button>')
    expect(teacherDetail).not.toContain('AI 预审材料</RouterLink>')
    expect(teacherTemplate).not.toContain('type="button" :disabled="!isPrimary">保存范本</button>')
    expect(content).not.toContain('>阅读案例</button>')
    expect(content).not.toContain('>查看详情</button>')
    expect(content).not.toContain('>查看公告</button>')
    expect(platform).not.toContain('>筛选</button>')
    expect(settings).not.toContain('查看操作记录')
  })
})
