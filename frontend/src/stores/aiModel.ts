import type { AIAgent, AIContextScope } from '../api'

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
