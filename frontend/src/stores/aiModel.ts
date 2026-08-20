import type { AIAgent, AIContextScope } from '../api'

export type AITrack = 'proposal' | 'paper'
export type PaperType = 'empirical' | 'case' | 'literature-review' | 'theoretical'

export interface AIArtifact { key: string; workflow: string; title: string; description: string; agentKey: string }
export interface PaperTypeOption { key: PaperType; label: string; description: string }
export interface AIWorkflowAgent { key: string; name: string; workflow: string; stage: string; quickActions: string[] }

export const AI_PROPOSAL_ARTIFACTS: AIArtifact[] = [
  { key: 'topic', workflow: 'proposal_topic', title: '课题名称与摘要', description: '聚焦研究问题，形成可申报的课题表述。', agentKey: 'topic-proposal' },
  { key: 'background', workflow: 'proposal_background', title: '研究背景与意义', description: '说明真实问题、研究价值与应用场景。', agentKey: 'opening-report' },
  { key: 'objectives', workflow: 'proposal_objectives', title: '研究目标与内容', description: '拆解目标、研究内容和关键问题。', agentKey: 'research-design-proposal' },
  { key: 'plan', workflow: 'proposal_plan', title: '实施方案与进度', description: '形成方法、分工、时间线与风险控制。', agentKey: 'feasibility-risk-proposal' },
  { key: 'outcomes', workflow: 'proposal_outcomes', title: '预期成果与经费', description: '明确可验证成果、展示形式和资源需求。', agentKey: 'proposal-polish' },
]

export const PAPER_TYPES: PaperTypeOption[] = [
  { key: 'empirical', label: '实证研究', description: '以数据、实验或问卷检验研究问题。' },
  { key: 'case', label: '案例研究', description: '围绕一个具体对象展开深度分析。' },
  { key: 'literature-review', label: '文献综述', description: '系统梳理已有研究并找出空白。' },
  { key: 'theoretical', label: '理论研究', description: '以概念辨析和逻辑论证构建观点。' },
]

const PAPER_AGENT_DEFINITIONS: AIWorkflowAgent[] = [
  { key: 'topic-selection-paper', name: '论文选题与标题', workflow: 'paper_topic', stage: '选题', quickActions: ['生成标题', '缩小选题'] },
  { key: 'paper-framework', name: '论文框架生成', workflow: 'paper_framework', stage: '框架', quickActions: ['生成论文框架', '调整章节'] },
  { key: 'literature-review-paper', name: '文献综述与检索', workflow: 'paper_literature', stage: '综述', quickActions: ['制定检索式', '生成综述提纲'] },
  { key: 'research-design-paper', name: '论文研究设计', workflow: 'paper_design', stage: '设计', quickActions: ['设计研究方法', '规划数据分析'] },
  { key: 'results-discussion-paper', name: '结果与讨论写作', workflow: 'paper_analysis', stage: '分析', quickActions: ['解读结果', '起草讨论'] },
  { key: 'paper-polish', name: '论文润色与规范检查', workflow: 'paper_review', stage: '校对', quickActions: ['润色论文', '检查引用格式'] },
]

export function paperAgentsForType(_type: PaperType): AIWorkflowAgent[] {
  return PAPER_AGENT_DEFINITIONS
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

export function aiQuickEntryLocation(taskId: number, workflow: string, agent: string) {
  return `/student/ai?taskId=${taskId}&workflow=${encodeURIComponent(workflow)}&agent=${encodeURIComponent(agent)}`
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
