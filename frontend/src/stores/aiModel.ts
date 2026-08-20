import type { AIAgent, AIContextScope, VerificationItem } from '../api'

export type AITrack = 'proposal' | 'paper'
export type PaperType = 'empirical' | 'case' | 'literature-review' | 'theoretical'

export interface AIArtifact { key: string; workflow: string; title: string; description: string; agentKey: string }
export interface PaperTypeOption { key: PaperType; label: string; description: string }
export interface AIWorkflowAgent { key: string; name: string; workflow: string; stage: string; quickActions: string[]; typeHint?: string }

export const AI_PROPOSAL_ARTIFACTS: AIArtifact[] = [
  { key: 'topic', workflow: 'proposal_topic', title: '课题名称与摘要', description: '聚焦研究问题，形成可申报的课题表述。', agentKey: 'proposal-topic' },
  { key: 'background', workflow: 'proposal_background', title: '研究背景与意义', description: '说明真实问题、研究价值与应用场景。', agentKey: 'proposal-background' },
  { key: 'objectives', workflow: 'proposal_objectives', title: '研究目标与内容', description: '拆解目标、研究内容和关键问题。', agentKey: 'proposal-objectives' },
  { key: 'plan', workflow: 'proposal_plan', title: '实施方案与进度', description: '形成方法、分工、时间线与风险控制。', agentKey: 'proposal-plan' },
  { key: 'consistency', workflow: 'proposal_consistency', title: '申报材料一致性检查', description: '核对问题、目标、方法、进度与成果是否前后一致。', agentKey: 'proposal-consistency' },
]

export const PAPER_TYPES: PaperTypeOption[] = [
  { key: 'empirical', label: '实证研究', description: '以数据、实验或问卷检验研究问题。' },
  { key: 'case', label: '案例研究', description: '围绕一个具体对象展开深度分析。' },
  { key: 'literature-review', label: '文献综述', description: '系统梳理已有研究并找出空白。' },
  { key: 'theoretical', label: '理论研究', description: '以概念辨析和逻辑论证构建观点。' },
]

const PAPER_AGENT_DEFINITIONS: AIWorkflowAgent[] = [
  { key: 'paper-title-abstract', name: '标题与摘要助手', workflow: 'paper_title_abstract', stage: '标题与摘要', quickActions: ['生成标题', '起草摘要'] },
  { key: 'paper-framework', name: '论文框架助手', workflow: 'paper_framework', stage: '框架', quickActions: ['生成论文框架', '调整章节'] },
  { key: 'paper-expand-polish', name: '扩写与润色助手', workflow: 'paper_expand_polish', stage: '扩写与润色', quickActions: ['扩写段落', '润色论文'] },
  { key: 'paper-reference-format', name: '参考文献格式助手', workflow: 'paper_reference_format', stage: '参考文献', quickActions: ['整理参考文献', '检查格式'] },
  { key: 'paper-result-interpret', name: '结果解读助手', workflow: 'paper_results_interpretation', stage: '结果解读', quickActions: ['解读结果', '梳理讨论'] },
  { key: 'paper-reviewer-response', name: '审稿意见回复助手', workflow: 'paper_reviewer_response', stage: '审稿回复', quickActions: ['拆解意见', '起草回复'] },
]

const PAPER_TYPE_EXPERIENCES: Record<PaperType, { label: string; promptPrefix: string; toolHints: string[] }> = {
  empirical: { label: '实证研究', promptPrefix: '论文类型：实证研究。请围绕可检验的问题、研究设计、变量与真实数据证据组织草稿；不要虚构统计结果。', toolHints: ['突出可检验的问题与摘要要素', '按研究问题、研究设计、结果与讨论搭建结构', '保留数据来源和统计验证位置', '标出需要追溯的实证研究来源', '区分观察结果与统计验证结论', '逐条回应方法、数据与结论质疑'] },
  case: { label: '案例研究', promptPrefix: '论文类型：案例研究。请围绕具体案例、证据链、情境边界与可迁移性组织草稿；不要补造案例事实。', toolHints: ['突出案例对象、情境与核心发现', '按案例背景、证据、分析与启示搭建结构', '保留案例证据来源与时间线', '标出案例资料的原始出处', '区分案例描述、分析与推论', '逐条回应案例代表性和证据链质疑'] },
  'literature-review': { label: '文献综述', promptPrefix: '论文类型：文献综述。请围绕系统检索、筛选标准、主题脉络与研究空白组织草稿；不要编造文献或引文。', toolHints: ['突出研究主题、范围与综述价值', '按检索策略、筛选标准、主题综述与空白搭建结构', '保留检索式、数据库和筛选记录位置', '只生成格式核对与待检索来源，不编造文献', '区分文献发现、综合判断与待验证空白', '逐条回应检索范围和纳排标准质疑'] },
  theoretical: { label: '理论研究', promptPrefix: '论文类型：理论研究。请围绕概念界定、逻辑推演、论证边界与反例组织草稿；不要将推演写成已证实事实。', toolHints: ['突出核心概念、论题与理论贡献', '按概念界定、论证路径、反例与结论搭建结构', '保留关键前提和反例检验位置', '标出需核验的理论来源和概念出处', '区分逻辑推演、假设与可验证结论', '逐条回应前提、推理和适用边界质疑'] },
}

export function paperAgentsForType(type: PaperType): AIWorkflowAgent[] {
  return PAPER_AGENT_DEFINITIONS.map((agent, index) => ({ ...agent, typeHint: PAPER_TYPE_EXPERIENCES[type].toolHints[index] }))
}

export function paperGenerationContext(type: PaperType) {
  const experience = PAPER_TYPE_EXPERIENCES[type]
  return { paper_type: type, paper_type_label: experience.label, promptPrefix: experience.promptPrefix }
}

export function agentInputValues(agent: AIAgent | null, prompt: string, projectTitle: string, paperTypeLabel?: string): Record<string, string> | undefined {
  if (!agent?.input_schema?.length) return undefined
  return Object.fromEntries(agent.input_schema.map((field) => [
    field.key,
    field.key === 'paper_type' ? (paperTypeLabel || '') : field.key === 'project_title' ? projectTitle : prompt,
  ]))
}

export function verificationItemsForDisplay(items?: Array<VerificationItem | string>): VerificationItem[] {
  if (!items?.length) return [{ item: '核对全部事实、数据和引用来源。', status: 'needs_verification', guidance: '' }]
  return items.map((check) => typeof check === 'string'
    ? { item: check, status: 'needs_verification', guidance: '' }
    : { item: check.item, status: check.status || 'needs_verification', guidance: check.guidance || '' })
}

export function agentMetadata(agent: AIAgent): AIWorkflowAgent {
  return {
    key: agent.key,
    name: agent.name,
    workflow: agent.workflow || (agent.key.includes('literature') ? 'paper_literature' : agent.key.includes('design') ? 'paper_design' : 'paper_writing'),
    stage: agent.applicable_stages?.[0] || agent.category || '写作',
    quickActions: agent.quick_tasks?.length ? agent.quick_tasks : ['生成草稿'],
  }
}

export function aiQuickEntryLocation(projectId: number, taskId: number, workflow: string, agent: string) {
  return `/student/ai?projectId=${projectId}&taskId=${taskId}&workflow=${encodeURIComponent(workflow)}&agent=${encodeURIComponent(agent)}`
}

export function resolveAIEntryProjectId(queryProjectId: unknown, projects: Array<{ id: number }>): number | null {
  const candidate = typeof queryProjectId === 'string' ? Number(queryProjectId) : queryProjectId
  if (typeof candidate === 'number' && Number.isSafeInteger(candidate) && projects.some((project) => project.id === candidate)) return candidate
  return projects[0]?.id ?? null
}

export type AIStatus = 'queued' | 'processing' | 'completed' | 'failed'
export const shouldPollAI = (status: AIStatus) => status === 'queued' || status === 'processing'
export const aiStatusLabel = (status: AIStatus) => ({ queued: '排队中', processing: '生成中', completed: '已完成', failed: '生成失败' }[status])

export const canGenerateAI = (serviceStatus: string | null) =>
  serviceStatus === 'configured' || serviceStatus === 'demo_mode'

export const isAIDemoMode = (serviceStatus: string | null) => serviceStatus === 'demo_mode'

export function normalizeAISelection(selected: string, availableTools: string[]) {
  return availableTools.includes(selected) ? selected : availableTools[0] ?? ''
}

export function normalizeAIAgentSelection(selected: AIAgent | null, agents: AIAgent[]): AIAgent | null {
  if (selected && agents.some((a) => a.id === selected.id)) return selected
  return agents[0] ?? null
}

/** 将 agent 的提示词模板中的 {变量} 用用户输入替换；缺失变量替换为空串。 */
export function composeAgentPrompt(template: AIAgent, values: Record<string, string>): string {
  return template.prompt_template.replace(/\{(\w+)\}/g, (_, key: string) => values[key] ?? '')
}

export function aiUnavailableMessage(serviceStatus: string | null): string {
  if (serviceStatus === 'demo_mode') return '当前为演示模式：AI 未接入真实模型，将返回示例性建议，仅供演示。'
  if (serviceStatus === 'not_configured') return 'AI 服务尚未配置，请联系平台管理员。'
  if (serviceStatus === 'quota_exhausted') return '本校本月 AI 配额已用完，请联系平台管理员扩容。'
  if (serviceStatus === 'unavailable') return 'AI 服务当前不可用，请稍后重试。'
  return '正在检查 AI 服务状态，请稍后再试。'
}

export function aiHistoryMeta(input: { actorName: string; scope: AIContextScope }) {
  const labels = [
    input.scope.project_basics ? '项目基础信息' : '',
    input.scope.approved_materials ? '已通过材料' : '',
  ].filter(Boolean)
  return `${input.actorName} · ${labels.join('、') || '未使用项目资料'}`
}
