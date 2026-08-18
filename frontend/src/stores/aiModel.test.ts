import { describe, expect, it } from 'vitest'

import type { AIAgent } from '../api'
import { aiStatusLabel, aiUnavailableMessage, canGenerateAI, composeAgentPrompt, normalizeAIAgentSelection, normalizeAISelection, shouldPollAI } from './aiModel'
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
