import { describe, expect, it } from 'vitest'
import { aiWorkspaceMode, buildResearchQuestionPrompt, groupAgentsByCategory, normalizeResearchQuestionArtifact, optionalAgentInputs, parseSSEChunk, conversationTitle, filterConversations, isNearBottom, isTerminalSSEEvent, researchProjectDraftFromArtifact, researchResponseNotice, type AIConversation } from './aiConversationModel'

describe('ai conversation model', () => {
  it('omits an empty Agent input object so the API can use the prompt fallback', () => {
    expect(optionalAgentInputs({})).toBeUndefined()
    expect(optionalAgentInputs({ topic: '  ', observations: '雨水积水' })).toEqual({ observations: '雨水积水' })
  })
  it('parses complete SSE events and keeps incomplete tail for the next chunk', () => {
    const first = parseSSEChunk('id: 7\nevent: message.delta\ndata: {"delta":"你好"}\n\npartial')
    expect(first.events).toEqual([{ id: '7', event: 'message.delta', data: { delta: '你好' } }])
    expect(first.rest).toBe('partial')
    const second = parseSSEChunk(`${first.rest}\n\nevent: message.done\ndata: {"message_id":9}\n\n`)
    expect(second.events[0]).toEqual({ id: undefined, event: 'message.done', data: { message_id: 9 } })
  })

  it('creates a useful title and filters archived/project conversations', () => {
    expect(conversationTitle('研究校园雨水花园的可行性')).toBe('研究校园雨水花园的可行性')
    expect(conversationTitle('这是一个非常长的对话标题，应该被截断为适合侧栏展示的简短标题')).toHaveLength(24)
    const conversations: AIConversation[] = [
      { id: 1, title: '项目一', project: 10, project_title: '项目一', paper_type: null, current_agent: null, is_archived: false, updated_at: '2026-08-20T09:00:00Z', created_at: '2026-08-20T09:00:00Z' },
      { id: 2, title: '归档', project: 10, project_title: '项目一', paper_type: null, current_agent: null, is_archived: true, updated_at: '2026-08-20T10:00:00Z', created_at: '2026-08-20T10:00:00Z' },
    ]
    expect(filterConversations(conversations, { project: 10, includeArchived: false })).toHaveLength(1)
    expect(filterConversations(conversations, { project: null, includeArchived: true })).toHaveLength(2)
  })
  it('detects when the chat is close enough to the bottom for safe auto-scroll', () => {
    expect(isNearBottom({ scrollTop: 740, clientHeight: 400, scrollHeight: 1200 })).toBeTruthy()
    expect(isNearBottom({ scrollTop: 500, clientHeight: 400, scrollHeight: 1200 })).toBeFalsy()
    expect(isNearBottom({ scrollTop: 500, clientHeight: 400, scrollHeight: 1200, threshold: 300 })).toBeTruthy()
  })
  it('recognizes terminal SSE events separately from progress events', () => {
    expect(isTerminalSSEEvent('message.done')).toBeTruthy()
    expect(isTerminalSSEEvent('message.error')).toBeTruthy()
    expect(isTerminalSSEEvent('message.delta')).toBeFalsy()
    expect(isTerminalSSEEvent('message.artifact')).toBeFalsy()
  })
  it('turns an unavailable research response into an actionable notice', () => {
    expect(researchResponseNotice({ status: 'failed', content: '', error_message: 'upstream timeout' })).toBe('研究问题助手暂时无法生成候选，请稍后重试。')
    expect(researchResponseNotice({ status: 'streaming', content: '', error_message: '' })).toBe('研究问题助手响应超时，候选尚未生成；请稍后重试。')
    expect(researchResponseNotice({ status: 'completed', content: '', error_message: '' })).toBe('研究问题助手返回内容不完整，请重新生成。')
    expect(researchResponseNotice({ status: 'completed', content: '{"candidates":[]}', error_message: '' })).toBe('')
  })
  it('groups visible Agents by category while preserving their order', () => {
    const groups = groupAgentsByCategory([
      { key: 'a', category: '开题申报', name: '课题助手' },
      { key: 'b', category: '论文写作', name: '论文助手' },
      { key: 'c', category: '开题申报', name: '背景助手' },
      { key: 'd', category: '', name: '通用助手' },
    ])
    expect(groups.map((group) => group.category)).toEqual(['开题申报', '论文写作', '其他'])
    expect(groups[0].agents.map((agent) => agent.key)).toEqual(['a', 'c'])
    expect(groups[2].agents[0].name).toBe('通用助手')
  })
  it('keeps no-project brainstorming separate from an existing-project workspace', () => {
    expect(aiWorkspaceMode({ brainstorm: true, researchQuestion: false, projectId: null, conversationProject: null })).toBe('brainstorm')
    expect(aiWorkspaceMode({ brainstorm: false, researchQuestion: true, projectId: 8, conversationProject: 8 })).toBe('project')
    expect(aiWorkspaceMode({ brainstorm: false, researchQuestion: true, projectId: null, conversationProject: null })).toBe('brainstorm')
    expect(aiWorkspaceMode({ brainstorm: false, researchQuestion: false, projectId: null, conversationProject: null, selectedAgent: 'proposal-topic' })).toBe('general')
  })
  it('normalizes three structured research-question candidates and clamps scores', () => {
    const artifact = normalizeResearchQuestionArtifact({
      project_title: '校园积水与通行安全',
      project_type: 'engineering',
      project_plan: '连续观察积水位置，并比较排水条件。',
      candidates: [
        { question: '问题一', scope: '校园', why: '有价值', evidence_plan: '观察', limitations: '时间', scores: { researchability: 7, clarity: 0, verifiability: 4, resource_fit: 3 } },
        { question: '问题二', scores: { researchability: 3, clarity: 4, verifiability: 5, resource_fit: 2 } },
        { question: '问题三', scores: { researchability: 1, clarity: 2, verifiability: 3, resource_fit: 4 } },
      ], recommended_index: 1,
    })
    expect(artifact?.candidates).toHaveLength(3)
    expect(artifact?.candidates[0].scores).toEqual({ researchability: 5, clarity: 1, verifiability: 4, resource_fit: 3 })
    expect(artifact?.recommended_index).toBe(1)
    expect(artifact).toMatchObject({
      project_title: '校园积水与通行安全',
      project_type: 'engineering',
      project_plan: '连续观察积水位置，并比较排水条件。',
    })
  })
  it('returns null for malformed research-question output so the UI can use editable text fallback', () => {
    expect(normalizeResearchQuestionArtifact({ candidates: [{ question: '', scores: {} }] })).toBeNull()
    expect(normalizeResearchQuestionArtifact({ candidates: [{ question: '只有一个', scores: { researchability: 3, clarity: 3, verifiability: 3, resource_fit: 3 } }] })).toBeNull()
  })
  it('turns the selected candidate into an editable project draft', () => {
    const artifact = normalizeResearchQuestionArtifact({
      project_title: '校园雨水观察', project_type: 'engineering', project_plan: '连续记录积水位置和持续时间。',
      candidates: [
        { question: '问题一', scores: { researchability: 3, clarity: 3, verifiability: 3, resource_fit: 3 } },
        { question: '问题二', evidence_plan: '比较不同位置的积水变化。', scores: { researchability: 4, clarity: 4, verifiability: 4, resource_fit: 4 } },
        { question: '问题三', scores: { researchability: 2, clarity: 2, verifiability: 2, resource_fit: 2 } },
      ], recommended_index: 1,
    })
    expect(researchProjectDraftFromArtifact(artifact, 1)).toEqual({
      title: '校园雨水观察', problem: '问题二', plan: '连续记录积水位置和持续时间。', project_type: 'engineering',
    })
    expect(researchProjectDraftFromArtifact(null, null, '手动补充的问题')).toMatchObject({ title: '手动补充的问题', problem: '手动补充的问题', project_type: 'research' })
  })
  it('builds the guided prompt once from phenomenon, boundaries and constraints', () => {
    const prompt = buildResearchQuestionPrompt({ phenomenon: '雨天操场积水', object_context: '校园操场', goal: '找出积水原因', constraints: '只有两周和手机' })
    expect(prompt.match(/雨天操场积水/g)).toHaveLength(1)
    expect(prompt).toContain('校园操场')
    expect(prompt).toContain('只生成 3 个候选')
    expect(prompt).toContain('两周和手机')
    expect(prompt).toContain('project_title')
    expect(prompt).toContain('project_plan')
  })
})
