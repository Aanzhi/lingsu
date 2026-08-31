import { describe, expect, it } from 'vitest'
import type { AIAgent } from '../api'
import { AI_WORKBENCH_MODES, draftActions, materialSelectionScope, resolveAIContext, resolveStudentAgent, starterPrompts, visibleAgents, workbenchPaths, workspaceModeDescription, type AIWorkspaceMode } from './aiWorkbenchModel'

const agent = (overrides: Partial<AIAgent>): AIAgent => ({
  id: 1,
  key: 'agent',
  name: '科创助手',
  description: '辅助研究',
  role: 'student',
  category: '研究',
  system_instruction: '',
  prompt_template: '',
  input_schema: [],
  context_scope_default: {},
  is_active: true,
  school: null,
  order: 1,
  workflow: 'research',
  ...overrides,
})

describe('AI workbench model', () => {
  it('exposes the three student AI modes in product order', () => {
    expect(AI_WORKBENCH_MODES.map((item) => item.key)).toEqual(['opening', 'research', 'defense'])
  })

  it('returns three starter prompts for each workbench mode', () => {
    for (const { key: mode } of AI_WORKBENCH_MODES) {
      const prompts = starterPrompts(mode)
      const expectedPrompts = [...prompts]
      expect(prompts).toHaveLength(3)
      expect(prompts.every((prompt) => prompt.length > 6)).toBe(true)
      expect(starterPrompts(mode)).not.toBe(prompts)
      prompts[0] = '本地修改不应污染默认提示'
      expect(starterPrompts(mode)).toEqual(expectedPrompts)
    }
    expect(starterPrompts('research')).toEqual([
      '帮我拆解今天的研究任务',
      '如何设计下一步实验？',
      '怎样整理现有证据？',
    ])
  })

  it('derives useful work paths from available Skills instead of prompt fragments', () => {
    const paths = workbenchPaths([
      agent({ key: 'proposal-topic', name: '研究问题助手', description: '把观察收敛为可研究的问题。', workflow: 'proposal_topic', quick_tasks: ['选题建议', '问题澄清'], input_schema: [{ key: 'topic', label: '项目主题', placeholder: '你想研究的主题', required: true, type: 'text' }] }),
      agent({ key: 'proposal-objectives', name: '研究目标与内容', description: '把问题转成可执行方案。', workflow: 'proposal_objectives', quick_tasks: ['设计实验'], input_schema: [{ key: 'research_question', label: '研究问题', placeholder: '要回答的问题', required: true, type: 'text' }] }),
      agent({ key: 'proposal-consistency', name: '一致性检查', description: '检查开题材料的逻辑。', workflow: 'proposal_consistency', quick_tasks: ['检查证据缺口'], input_schema: [{ key: 'draft', label: '申报材料', placeholder: '粘贴申报书片段', required: true, type: 'textarea' }] }),
      agent({ key: 'extra', name: '不应显示的第四项', quick_tasks: ['不应出现'] }),
    ])

    expect(paths).toHaveLength(3)
    expect(paths[0]).toMatchObject({ agentKey: 'proposal-topic', title: '研究问题助手', output: expect.stringContaining('选题建议'), inputHint: expect.stringContaining('你想研究的主题') })
    expect(paths.every((path) => path.description && path.output && path.inputHint)).toBe(true)
  })

  it('uses the Skill description as the work result when no quick task is configured', () => {
    const [path] = workbenchPaths([agent({ key: 'opening-report', name: '开题报告助手', description: '梳理论证链条与开题结构。', quick_tasks: [] })])

    expect(path.output).toContain('梳理论证链条与开题结构')
  })

  it('maps research and defense to the current project', () => {
    expect(resolveAIContext('research', 8)).toEqual({ projectId: 8, scope: 'current_project' })
    expect(resolveAIContext('defense', 8)).toEqual({ projectId: 8, scope: 'current_project' })
  })

  it('uses mode responsibilities for the assistant bar copy', () => {
    expect(workspaceModeDescription('opening')).toBe('直接说出要处理的研究问题，不需要先填写表格。')
    expect(workspaceModeDescription('research')).toBe('围绕当前项目的任务、材料和进度，推进下一步研究工作。')
    expect(workspaceModeDescription('defense')).toBe('整理摘要、展示内容和答辩表达。')
  })

  it('keeps opening project-free even when a current project exists', () => {
    expect(resolveAIContext('opening', 8)).toEqual({ projectId: null, scope: 'none' })
    expect(resolveAIContext('opening', null)).toEqual({ projectId: null, scope: 'none' })
  })

  it('assigns every student Agent to exactly one workbench mode', () => {
    const agents = [
      agent({ id: 1, key: 'opening-agent', category: '开题', workflow: 'opening' }),
      agent({ id: 2, key: 'research-agent', category: '研究', workflow: 'research' }),
      agent({ id: 3, key: 'defense-agent', category: '答辩', workflow: 'defense' }),
      agent({ id: 4, key: 'proposal-background', category: '开题申报', workflow: 'proposal_background' }),
      agent({ id: 5, key: 'report-agent', category: '论文写作', workflow: 'paper_expand_polish' }),
    ]
    expect(visibleAgents('opening', agents).map((item) => item.key)).toEqual(['opening-agent', 'proposal-background'])
    expect(visibleAgents('research', agents).map((item) => item.key)).toEqual(['research-agent', 'report-agent'])
    expect(visibleAgents('defense', agents).map((item) => item.key)).toEqual(['defense-agent'])
  })

  it('resolves a deterministic internal student Agent without exposing it in the UI', () => {
    const agents = [
      agent({ id: 1, key: 'opening-late', name: '后置开题助手', category: '开题', workflow: 'opening', order: 2 }),
      agent({ id: 2, key: 'opening-first', name: '默认开题助手', category: '开题', workflow: 'opening', order: 1 }),
      agent({ id: 3, key: 'research-disabled', category: '研究', workflow: 'research', is_active: false, order: 0 }),
    ]
    expect(resolveStudentAgent('opening', agents)).toMatchObject({ key: 'opening-first' })
    expect(resolveStudentAgent('opening', agents, 'opening-late')).toMatchObject({ key: 'opening-late' })
    expect(resolveStudentAgent('opening', agents, 'missing')).toMatchObject({ key: 'opening-first' })
    expect(resolveStudentAgent('opening', agents, 'opening-late', 'opening-first')).toMatchObject({ key: 'opening-first' })
    expect(resolveStudentAgent('research', agents)).toBeNull()
  })

  it('requires an explicit action for completed drafts', () => {
    expect(draftActions('completed')).toEqual(['save_material', 'create_project_from_opening'])
    expect(draftActions('streaming')).toEqual([])
  })

  it('keeps mode input narrow and deterministic', () => {
    const modes: AIWorkspaceMode[] = ['opening', 'research', 'defense']
    expect(modes).toHaveLength(3)
  })

  it('only sends explicitly selected materials for a project-capable Agent', () => {
    expect(materialSelectionScope('opening', [4], ['selected_materials'])).toEqual({})
    expect(materialSelectionScope('research', [4, 4, 9], [])).toEqual({})
    expect(materialSelectionScope('research', [4, 4, 9], ['selected_materials'])).toEqual({ selected_materials: [4, 9] })
  })
})
