import { describe, expect, it } from 'vitest'

/**
 * 任务-材料-交付物的映射规则：
 * - 有 material.task === task.id 时：
 *     - 名称 = material.report_section ?? material.title（这就是报告里出现的章节名）
 *     - 副名 = material.title
 *     - material.status === 'approved' → delivered；否则 in_progress
 * - 无 material 但 task.status === 'approved' / 'completed' → delivered
 * - 无 material 且 task.status === 'pending_review' / 'submitted' / 'revision_required' → in_progress
 * - task.status === 'locked' → locked
 * - 其它 → pending
 * 名称兜底 = task.title（不再做 12 字截断）
 */

interface FakeTask { id: number; status: string; title: string; evidence_requirements: string[] }
interface FakeMaterial { id: number; task: number | null; title: string; status: string; report_section?: string }

function mapDelivery(task: FakeTask, material: FakeMaterial | undefined) {
  let status: 'delivered' | 'in_progress' | 'pending' | 'locked' = 'pending'
  let label = task.title
  let subLabel: string | null = task.evidence_requirements[0] ?? null
  if (material) {
    label = material.report_section || material.title
    subLabel = material.title
    status = material.status === 'approved' ? 'delivered' : 'in_progress'
  } else if (task.status === 'approved' || task.status === 'completed') {
    status = 'delivered'
  } else if (['pending_review', 'submitted', 'revision_required'].includes(task.status)) {
    status = 'in_progress'
  } else if (task.status === 'locked') {
    status = 'locked'
  }
  return { status, label, subLabel }
}

describe('journey delivery mapping', () => {
  it('uses report_section as label and material title as subLabel when material exists', () => {
    const t: FakeTask = { id: 1, status: 'available', title: '问题定义', evidence_requirements: ['开题报告'] }
    const m: FakeMaterial = { id: 10, task: 1, title: '问题定义材料', status: 'approved', report_section: '研究问题' }
    expect(mapDelivery(t, m)).toEqual({ status: 'delivered', label: '研究问题', subLabel: '问题定义材料' })
  })

  it('falls back to material title when report_section is empty', () => {
    const t: FakeTask = { id: 2, status: 'pending_review', title: '方案草图', evidence_requirements: [] }
    const m: FakeMaterial = { id: 11, task: 2, title: '设计方案', status: 'submitted' }
    expect(mapDelivery(t, m)).toEqual({ status: 'in_progress', label: '设计方案', subLabel: '设计方案' })
  })

  it('in_progress when material is submitted but not approved', () => {
    const t: FakeTask = { id: 3, status: 'available', title: '3D 模型', evidence_requirements: [] }
    const m: FakeMaterial = { id: 12, task: 3, title: '3D 模型 V1', status: 'submitted', report_section: '研究过程' }
    expect(mapDelivery(t, m)).toEqual({ status: 'in_progress', label: '研究过程', subLabel: '3D 模型 V1' })
  })

  it('pending when no material and task is available, label = task.title', () => {
    const t: FakeTask = { id: 4, status: 'available', title: '接线图', evidence_requirements: [] }
    expect(mapDelivery(t, undefined)).toEqual({ status: 'pending', label: '接线图', subLabel: null })
  })

  it('delivered when task is approved without any material, label = task.title', () => {
    const t: FakeTask = { id: 5, status: 'approved', title: '项目视频', evidence_requirements: [] }
    expect(mapDelivery(t, undefined)).toEqual({ status: 'delivered', label: '项目视频', subLabel: null })
  })

  it('locked when task is locked', () => {
    const t: FakeTask = { id: 6, status: 'locked', title: '源文件', evidence_requirements: [] }
    expect(mapDelivery(t, undefined)).toEqual({ status: 'locked', label: '源文件', subLabel: null })
  })

  it('in_progress when task is pending_review without material', () => {
    const t: FakeTask = { id: 7, status: 'pending_review', title: '答辩稿', evidence_requirements: [] }
    expect(mapDelivery(t, undefined)).toEqual({ status: 'in_progress', label: '答辩稿', subLabel: null })
  })
})
