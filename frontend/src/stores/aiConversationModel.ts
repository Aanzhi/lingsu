export interface AIConversation {
  id: number
  title: string
  project: number | null
  project_title: string | null
  paper_type: string | null
  current_agent: string | null
  is_archived: boolean
  updated_at: string
  created_at: string
}

export type AIWorkspaceMode = 'brainstorm' | 'project' | 'general'

export interface AIWorkspaceModeInput {
  brainstorm: boolean
  researchQuestion: boolean
  projectId: number | null
  conversationProject: number | null
  /** The selected Agent alone must not silently turn an unbound chat into a project workflow. */
  selectedAgent?: string | null
}

export function aiWorkspaceMode(input: AIWorkspaceModeInput): AIWorkspaceMode {
  if (input.brainstorm) return 'brainstorm'
  if (input.projectId !== null || input.conversationProject !== null) return 'project'
  if (input.researchQuestion) return 'brainstorm'
  return 'general'
}

export interface AIConversationMessage {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  status: 'queued' | 'streaming' | 'completed' | 'failed'
  generation?: number | null
  artifact_payload?: { title?: string; draft?: string; next_action?: string; project_title?: string; project_type?: 'research' | 'invention' | 'engineering'; project_plan?: string; candidates?: ResearchQuestionCandidate[]; recommended_index?: number; missing_information?: string[] } | null
  verification_items?: Array<{ item: string; status?: string; guidance?: string } | string>
  error_message?: string
  created_at: string
}

export interface ResearchQuestionScores {
  researchability: number
  clarity: number
  verifiability: number
  resource_fit: number
}

export interface ResearchQuestionCandidate {
  question: string
  scope: string
  why: string
  evidence_plan: string
  limitations: string
  scores: ResearchQuestionScores
}

export interface ResearchQuestionArtifact {
  project_title: string
  project_type: 'research' | 'invention' | 'engineering'
  project_plan: string
  candidates: ResearchQuestionCandidate[]
  recommended_index: number
  missing_information: string[]
}

export interface ResearchProjectDraft {
  title: string
  problem: string
  plan: string
  project_type: 'research' | 'invention' | 'engineering'
}

function clampScore(value: unknown): number | null {
  const number = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(number)) return null
  return Math.max(1, Math.min(5, Math.round(number)))
}

export function normalizeResearchQuestionArtifact(payload: unknown): ResearchQuestionArtifact | null {
  if (!payload || typeof payload !== 'object') return null
  const source = payload as Record<string, unknown>
  if (!Array.isArray(source.candidates) || source.candidates.length !== 3) return null
  const candidates: ResearchQuestionCandidate[] = []
  for (const raw of source.candidates) {
    if (!raw || typeof raw !== 'object') return null
    const candidate = raw as Record<string, unknown>
    const question = String(candidate.question || '').trim()
    const rawScores = candidate.scores && typeof candidate.scores === 'object' ? candidate.scores as Record<string, unknown> : {}
    const scores = {
      researchability: clampScore(rawScores.researchability),
      clarity: clampScore(rawScores.clarity),
      verifiability: clampScore(rawScores.verifiability),
      resource_fit: clampScore(rawScores.resource_fit),
    }
    if (!question || Object.values(scores).some((value) => value === null)) return null
    candidates.push({
      question,
      scope: String(candidate.scope || '').trim(),
      why: String(candidate.why || '').trim(),
      evidence_plan: String(candidate.evidence_plan || '').trim(),
      limitations: String(candidate.limitations || '').trim(),
      scores: scores as ResearchQuestionScores,
    })
  }
  const recommended = Number(source.recommended_index)
  const projectType = source.project_type === 'invention' || source.project_type === 'engineering' ? source.project_type : 'research'
  return {
    project_title: String(source.project_title || '').trim(),
    project_type: projectType,
    project_plan: String(source.project_plan || '').trim(),
    candidates,
    recommended_index: Number.isInteger(recommended) && recommended >= 0 && recommended < candidates.length ? recommended : 0,
    missing_information: Array.isArray(source.missing_information) ? source.missing_information.map(String).map((item) => item.trim()).filter(Boolean) : [],
  }
}

export function researchProjectDraftFromArtifact(artifact: ResearchQuestionArtifact | null, selectedIndex: number | null, fallback = ''): ResearchProjectDraft {
  const index = artifact && selectedIndex !== null && artifact.candidates[selectedIndex] ? selectedIndex : (artifact?.recommended_index ?? 0)
  const candidate = artifact?.candidates[index]
  const problem = candidate?.question.trim() || fallback.trim()
  const title = artifact?.project_title.trim() || problem.slice(0, 80) || '我的研究项目'
  const plan = artifact?.project_plan.trim() || candidate?.evidence_plan.trim() || ''
  return {
    title,
    problem,
    plan,
    project_type: artifact?.project_type || 'research',
  }
}

export interface ResearchQuestionInputs {
  phenomenon: string
  object_context: string
  goal: string
  constraints: string
}

export function buildResearchQuestionPrompt(inputs: ResearchQuestionInputs): string {
  return [
    '你是研究问题助手，请基于下面一次性提供的信息生成候选研究问题。',
    `观察到的现象或兴趣：${inputs.phenomenon.trim()}`,
    `研究对象与场景：${inputs.object_context.trim()}`,
    `想弄清楚的方向：${inputs.goal.trim()}`,
    `时间、设备、样本或资源限制：${inputs.constraints.trim() || '暂无补充限制'}`,
    '只生成 3 个候选，返回 JSON：project_title、project_type、project_plan、candidates、recommended_index、missing_information。每个候选必须包含 question、scope、why、evidence_plan、limitations，以及 scores（researchability、clarity、verifiability、resource_fit，均为 1-5）。不要编造数据或引用。',
  ].join('\n')
}

export interface ParsedSSEEvent { id?: string; event: string; data: Record<string, unknown> }

export interface ScrollMetrics { scrollTop: number; clientHeight: number; scrollHeight: number; threshold?: number }

export function isNearBottom({ scrollTop, clientHeight, scrollHeight, threshold = 96 }: ScrollMetrics): boolean {
  return scrollHeight - (scrollTop + clientHeight) <= threshold
}

export function isTerminalSSEEvent(event: string): boolean {
  return event === 'message.done' || event === 'message.error'
}

export function researchResponseNotice(message: Pick<AIConversationMessage, 'status' | 'content' | 'error_message'>): string {
  if (message.status === 'failed') return '研究问题助手暂时无法生成候选，请稍后重试。'
  if ((message.status === 'queued' || message.status === 'streaming') && !message.content?.trim()) {
    return '研究问题助手响应超时，候选尚未生成；请稍后重试。'
  }
  if (message.status === 'completed' && !message.content?.trim()) return '研究问题助手返回内容不完整，请重新生成。'
  return ''
}

export function optionalAgentInputs(inputs: Record<string, string>): Record<string, string> | undefined {
  const entries = Object.entries(inputs).filter(([, value]) => value.trim())
  return entries.length ? Object.fromEntries(entries) : undefined
}

export interface AgentCategoryGroup<T> { category: string; agents: T[] }

export function groupAgentsByCategory<T extends { category?: string }>(agents: T[]): AgentCategoryGroup<T>[] {
  const groups = new Map<string, T[]>()
  agents.forEach((agent) => {
    const category = agent.category?.trim() || '其他'
    const current = groups.get(category) || []
    current.push(agent)
    groups.set(category, current)
  })
  return Array.from(groups, ([category, groupedAgents]) => ({ category, agents: groupedAgents }))
}

export function parseSSEChunk(chunk: string): { events: ParsedSSEEvent[]; rest: string } {
  const blocks = chunk.split(/\r?\n\r?\n/)
  const rest = blocks.pop() || ''
  const events = blocks.flatMap((block) => {
    let id: string | undefined
    let event = 'message'
    const dataLines: string[] = []
    block.split(/\r?\n/).forEach((line) => {
      if (line.startsWith('id:')) id = line.slice(3).trim()
      else if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
    })
    if (!dataLines.length) return []
    try { return [{ id, event, data: JSON.parse(dataLines.join('\n')) as Record<string, unknown> }] }
    catch { return [{ id, event, data: { text: dataLines.join('\n') } }] }
  })
  return { events, rest }
}

export function conversationTitle(value: string): string {
  const compact = value.trim().replace(/\s+/g, ' ')
  return compact.slice(0, 24) || '新建科创对话'
}

export function filterConversations(conversations: AIConversation[], options: { project: number | null; includeArchived: boolean }): AIConversation[] {
  return conversations
    .filter((item) => options.includeArchived || !item.is_archived)
    .filter((item) => options.project === null || item.project === options.project)
    .sort((left, right) => right.updated_at.localeCompare(left.updated_at))
}
