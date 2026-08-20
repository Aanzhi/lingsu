import { describe, expect, it } from 'vitest'

import type { AIAgent } from '../api'
import {
  aiStatusLabel, aiUnavailableMessage, canGenerateAI, composeAgentPrompt, normalizeAIAgentSelection, normalizeAISelection,
  shouldPollAI, AI_PROPOSAL_ARTIFACTS, PAPER_TYPES, agentMetadata, aiQuickEntryLocation, paperAgentsForType,
  agentInputValues, paperGenerationContext, verificationItemsForDisplay,
} from './aiModel'
import { aiHistoryMeta } from './aiModel'

describe('AI request states', () => {
  it('polls queued work and surfaces failure honestly', () => {
    expect(shouldPollAI('queued')).toBe(true)
    expect(shouldPollAI('processing')).toBe(true)
    expect(shouldPollAI('completed')).toBe(false)
    expect(aiStatusLabel('failed')).toBe('生成失败')
  })
})

it('only enables generation when the AI service is configured', () => {
  expect(canGenerateAI('configured')).toBe(true)
  expect(canGenerateAI('not_configured')).toBe(false)
  expect(aiUnavailableMessage('not_configured')).toContain('尚未配置')
})

it('keeps the selected tool inside the current portal toolset', () => {
  expect(normalizeAISelection('问题梳理', ['审核风险检查', '反馈草稿'])).toBe('审核风险检查')
  expect(normalizeAISelection('反馈草稿', ['审核风险检查', '反馈草稿'])).toBe('反馈草稿')
})

it('makes the source and material scope visible to a guiding teacher', () => {
  expect(aiHistoryMeta({ actorName: '林同学', scope: { project_basics: true, approved_materials: true } })).toBe('林同学 · 项目基础信息、已通过材料')
})

it('composes agent prompt by substituting template variables', () => {
  const agent = { prompt_template: 'A {x} B {y}', input_schema: [] } as unknown as AIAgent
  expect(composeAgentPrompt(agent, { x: '1', y: '2' })).toBe('A 1 B 2')
  expect(composeAgentPrompt(agent, { x: '1' })).toBe('A 1 B ')
})

it('keeps a valid selected agent and falls back to the first', () => {
  const a = { id: 1 } as unknown as AIAgent
  const b = { id: 2 } as unknown as AIAgent
  expect(normalizeAIAgentSelection(a, [a, b])).toBe(a)
  expect(normalizeAIAgentSelection(b, [a, b])).toBe(b)
  expect(normalizeAIAgentSelection(b, [a])).toBe(a)
  expect(normalizeAIAgentSelection(null, [a, b])).toBe(a)
})

it('maps proposal work to five concrete artifacts', () => {
  expect(AI_PROPOSAL_ARTIFACTS).toHaveLength(5)
  expect(AI_PROPOSAL_ARTIFACTS.map((item) => item.workflow)).toEqual([
    'proposal_topic', 'proposal_background', 'proposal_objectives', 'proposal_plan', 'proposal_consistency',
  ])
  expect(AI_PROPOSAL_ARTIFACTS.map((item) => item.agentKey)).toEqual([
    'proposal-topic', 'proposal-background', 'proposal-objectives', 'proposal-plan', 'proposal-consistency',
  ])
})

it('supports all paper types and keeps six agents available for each type', () => {
  expect(PAPER_TYPES.map((item) => item.key)).toEqual(['empirical', 'case', 'literature-review', 'theoretical'])
  expect(paperAgentsForType('case')).toHaveLength(6)
  expect(paperAgentsForType('case').map((agent) => agent.key)).toEqual([
    'paper-title-abstract', 'paper-framework', 'paper-expand-polish', 'paper-reference-format', 'paper-result-interpret', 'paper-reviewer-response',
  ])
})

it('adapts paper tools and generation context to the selected paper type', () => {
  const empirical = paperAgentsForType('empirical')[1]
  const review = paperAgentsForType('literature-review')[1]

  expect(empirical.typeHint).toContain('研究设计')
  expect(review.typeHint).toContain('检索')
  expect(paperGenerationContext('literature-review')).toMatchObject({
    paper_type: 'literature-review',
    paper_type_label: '文献综述',
  })
  expect(paperGenerationContext('literature-review').promptPrefix).toContain('系统检索')
})

it('renders structured verification items without stringifying objects', () => {
  expect(verificationItemsForDisplay([
    { item: '样本量', status: 'needs_verification', guidance: '核对原始问卷和统计口径。' },
  ])).toEqual([
    { item: '样本量', status: 'needs_verification', guidance: '核对原始问卷和统计口径。' },
  ])
  expect(verificationItemsForDisplay()).toEqual([
    { item: '核对全部事实、数据和引用来源。', status: 'needs_verification', guidance: '' },
  ])
})

it('submits declared template fields instead of relying on the legacy free-form fallback', () => {
  const agent = {
    input_schema: [{ key: 'project_title' }, { key: 'research_question' }, { key: 'paper_type' }],
  } as AIAgent
  expect(agentInputValues(agent, '请分析现有观察', '校园雨水回收', '文献综述')).toEqual({
    project_title: '校园雨水回收', research_question: '请分析现有观察', paper_type: '文献综述',
  })
})

it('uses backend agent metadata for workflow, stage and quick actions', () => {
  const agent = { key: 'paper-framework', category: '写作', workflow: 'paper_writing', applicable_stages: ['drafting'], quick_tasks: ['outline'] } as unknown as AIAgent
  expect(agentMetadata(agent)).toMatchObject({ workflow: 'paper_writing', stage: 'drafting', quickActions: ['outline'] })
})

it('builds a task AI quick entry that preserves task, workflow and agent', () => {
  expect(aiQuickEntryLocation(42, 'proposal_plan', 'proposal-plan')).toBe('/student/ai?taskId=42&workflow=proposal_plan&agent=proposal-plan')
})
