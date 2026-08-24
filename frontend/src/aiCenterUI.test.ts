import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')
const history = readFileSync(new URL('./components/ai/AIConversationHistory.vue', import.meta.url), 'utf8')
const contextChooser = readFileSync(new URL('./components/ai/AIContextChooser.vue', import.meta.url), 'utf8')
const researchWizard = readFileSync(new URL('./components/ai/AIResearchWizard.vue', import.meta.url), 'utf8')
const surface = [source, history, contextChooser, researchWizard].join('\n')

describe('AI workbench information architecture', () => {
  it('has one visible new-conversation entry point', () => {
    expect(history.match(/@click="emit\('new'\)"/g) ?? []).toHaveLength(1)
  })

  it('labels the agent picker in language students can understand', () => {
    expect(source).toContain('科创 Agent')
    expect(source).not.toContain('>Agent（')
  })

  it('keeps the only new-conversation action available on mobile', () => {
    expect(source).not.toContain('.new-conversation{display:none}')
  })

  it('uses a real accessible label for the dynamic tool count', () => {
    expect(source).not.toContain('aria-label="Agent（{{ agents.length }}）"')
    expect(source).toContain(':aria-label="`选择 AI 工具（${agents.length} 个）${currentAgent ? ` · ${currentAgent.name}` : \'\'}`"')
  })

  it('puts the three student AI modes before the conversation', () => {
    expect(surface).toContain('ai-context-switch')
    expect(surface).toContain('开题与选题')
    expect(surface).toContain('AI 对话完善材料')
    expect(surface).toContain('科创 Agent')
    expect(contextChooser).toContain("(event: 'agent'): void")
    expect(source).toContain('goToBrainstorm')
    expect(source).toContain('goToExistingProject')
    expect(source).toContain('openScienceAgentPicker')
    expect(source).toContain('@agent="openScienceAgentPicker"')
  })

  it('keeps the no-topic path as a guided four-step flow', () => {
    expect(researchWizard).toContain('第 1 步 · 发现现象')
    expect(researchWizard).toContain('第 2 步 · 打开问题')
    expect(researchWizard).toContain('第 3 步 · 头脑风暴')
    expect(researchWizard).toContain('第 4 步 · 共同成题')
    expect(researchWizard).toContain('研究对象与场景')
    expect(researchWizard).toContain('你想弄清楚哪个方向')
    expect(researchWizard).toContain('确认并生成项目')
  })

  it('does not expose a freeform composer before a project context is chosen', () => {
    expect(source).toContain('v-if="(!researchMode && currentProject) || researchSaved"')
  })

  it('uses the Demo B layered workspace structure for the production page', () => {
    expect(source).toContain('<PageHeader')
    expect(source).toContain('ai-simple-layout')
    expect(source).toContain('ai-context-summary')
    expect(source).toContain('ai-guide-card')
    expect(source).toContain('ai-stepper-simple')
  })

  it('keeps the WorkBuddy composition explicit and confirmation-first', () => {
    const modeTabs = readFileSync(new URL('./components/ai/AIModeTabs.vue', import.meta.url), 'utf8')
    const composer = readFileSync(new URL('./components/ai/AIWorkbenchComposer.vue', import.meta.url), 'utf8')
    const contextDrawer = readFileSync(new URL('./components/ai/AIContextDrawer.vue', import.meta.url), 'utf8')
    const draftActions = readFileSync(new URL('./components/ai/AIDraftActions.vue', import.meta.url), 'utf8')
    expect(modeTabs).toContain('开题')
    expect(modeTabs).toContain('研究')
    expect(modeTabs).toContain('答辩')
    expect(composer).toContain('引用项目材料')
    expect(composer).toContain('发送')
    expect(contextDrawer).toContain('读取材料数')
    expect(contextDrawer).toContain('只读草稿')
    expect(draftActions).toContain('保存为材料')
    expect(draftActions).toContain('用此报告创建项目')
    expect(source).toContain('AIModeTabs')
    expect(source).toContain('AIWorkbenchComposer')
    expect(source).toContain('AIContextDrawer')
    expect(source).toContain('AIDraftActions')
    expect(source).not.toContain('自动保存到材料')
  })
})
