import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const styles = readFileSync(new URL('./styles/workspace.css', import.meta.url), 'utf8')
const contentLibrary = readFileSync(new URL('./pages/shared/ContentLibrary.vue', import.meta.url), 'utf8')
const invitations = readFileSync(new URL('./pages/student/StudentInvitations.vue', import.meta.url), 'utf8')

describe('shared content surfaces', () => {
  it('gives empty states the full content width and avoids duplicate error copy', () => {
    expect(styles).toContain('.case-grid > .empty-state, .competition-list > .empty-state { grid-column: 1 / -1; }')
    expect(styles).toContain('.announcement-timeline > .empty-state { width: 100%; }')
    expect(contentLibrary).toContain('v-if="error && !feedback"')
    expect(invitations).toContain('v-if="error && !feedback"')
  })

  it('defines the student case library as a completed-public showcase', () => {
    expect(contentLibrary).toContain('case-showcase')
    expect(contentLibrary).toContain('已完成公开')
    expect(contentLibrary).toContain('我的公开申请')
    expect(contentLibrary).not.toContain('filteredCases.slice(0, 3)')
    expect(contentLibrary).not.toContain('showcase-completion')
    expect(contentLibrary).not.toContain('showcase-path')
  })

  it('keeps applications in a two-column workspace and gives cases an independent detail route', () => {
    expect(contentLibrary).toContain('case-application-workspace')
    expect(contentLibrary).toContain('case-application-records')
    expect(contentLibrary).toContain('compact title="还没有公开申请"')
    expect(contentLibrary).toContain('studentCaseRoute')
    expect(contentLibrary).toContain('case-detail-view')
    expect(contentLibrary).not.toContain('selectedCase = item')
    expect(contentLibrary).not.toContain('case-showcase__layout')
    expect(contentLibrary).not.toContain('case-detail-panel')
    expect(contentLibrary).not.toContain('case-detail-dialog')
    expect(contentLibrary).toContain('selectedCase.selected_material_summaries')
    expect(contentLibrary).not.toContain('showcase-path')
    expect(contentLibrary).not.toContain('showcase-completion')
  })

  it('defines the approved full-width competition and announcement content streams', () => {
    expect(contentLibrary).toContain('resource-content-page')
    expect(contentLibrary).toContain('competition-feature')
    expect(contentLibrary).toContain('competition-list-row')
    expect(contentLibrary).toContain('announcement-feed')
    expect(contentLibrary).not.toContain('filteredCompetitions.slice(0, 3)')
    expect(contentLibrary).not.toContain('content-scope-note')
    expect(contentLibrary).not.toContain('<button class="secondary-button" type="button" @click="runSearch">筛选</button>')
  })
})
