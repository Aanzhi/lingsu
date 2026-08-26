import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

const source = readFileSync(new URL('./pages/shared/AICenter.vue', import.meta.url), 'utf8')
const history = readFileSync(new URL('./components/ai/AIConversationHistory.vue', import.meta.url), 'utf8')
const contextChooser = readFileSync(new URL('./components/ai/AIContextChooser.vue', import.meta.url), 'utf8')
const researchWizard = readFileSync(new URL('./components/ai/AIResearchWizard.vue', import.meta.url), 'utf8')
const modeTabs = readFileSync(new URL('./components/ai/AIModeTabs.vue', import.meta.url), 'utf8')
const toolPicker = readFileSync(new URL('./components/ai/AIToolPicker.vue', import.meta.url), 'utf8')
const surface = [source, history, contextChooser, researchWizard].join('\n')

describe('AI workbench information architecture', () => {
  it('has one visible new-conversation entry point', () => {
    expect(history.match(/@click="emit\('new'\)"/g) ?? []).toHaveLength(1)
  })

  it('labels the agent picker in language students can understand', () => {
    expect(modeTabs).toContain('当前模式的 Agent')
    expect(source).not.toContain('>Agent（')
  })

  it('keeps the only new-conversation action available on mobile', () => {
    expect(source).not.toContain('.new-conversation{display:none}')
  })

  it('uses a real accessible label for the dynamic tool count', () => {
    expect(toolPicker).not.toContain('aria-label="Agent（{{ agents.length }}）"')
    expect(toolPicker).toContain('aria-label="选择 AI 工具（平台模板）"')
  })

  it('puts the three student AI modes before the conversation', () => {
    expect(source).toContain('ai-workbench-mode-region')
    expect(modeTabs).toContain('开题')
    expect(modeTabs).toContain('研究')
    expect(modeTabs).toContain('成果表达')
    expect(modeTabs).toContain('当前模式的 Agent')
    expect(source).toContain('openScienceAgentPicker')
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

  it('uses one direct composer for all three modes and shows the selected agent', () => {
    expect(source.match(/<AIWorkbenchComposer/g) ?? []).toHaveLength(1)
    expect(source).toContain('agent-name="currentAgent?.name"')
    expect(source).toContain('selected-material-ids="selectedMaterialIds"')
    expect(source).toContain("workbenchMode.value === 'opening'")
    expect(source).toContain("workbenchMode.value === 'research'")
    expect(source).toContain("workbenchMode.value === 'defense'")
    expect(source).not.toContain('缺少信息时灵思会在对话中追问')
    expect(source).not.toContain('补充信息（可选）')
  })

  it('uses the project workspace layout while retaining the focused AI conversation surface', () => {
    expect(source).toContain('class="page ai-center-page ai-workbench-frame"')
    expect(source).toContain('ai-workbench-frame')
    expect(source).toContain('ai-workbench-conversation')
    expect(source).toContain('ai-conversation-stream')
    expect(source).toContain('selectedMaterialIds')
    expect(source).not.toContain('<PageHeader')
    expect(source).not.toContain('class="ai-scope-card"')
    expect(source).not.toContain('v-if="false"')
  })

  it('keeps the WorkBuddy composition explicit and confirmation-first', () => {
    const modeTabs = readFileSync(new URL('./components/ai/AIModeTabs.vue', import.meta.url), 'utf8')
    const composer = readFileSync(new URL('./components/ai/AIWorkbenchComposer.vue', import.meta.url), 'utf8')
    const contextDrawer = readFileSync(new URL('./components/ai/AIContextDrawer.vue', import.meta.url), 'utf8')
    const draftActions = readFileSync(new URL('./components/ai/AIDraftActions.vue', import.meta.url), 'utf8')
    expect(modeTabs).toContain('开题')
    expect(modeTabs).toContain('研究')
    expect(modeTabs).toContain('成果表达')
    expect(modeTabs).toContain('<strong>{{ agent.name }}</strong>')
    expect(composer).toContain('引用材料')
    expect(composer).toContain('当前 Agent')
    expect(composer).not.toContain('补充信息（可选）')
    expect(composer).not.toContain('inputSchema')
    expect(composer).toContain('selected-material')
    expect(composer).toContain('发送')
    expect(contextDrawer).toContain('已选材料')
    expect(contextDrawer).toContain('selectedMaterialIds')
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
