import type { Material } from '../api'
import type { TaskStatus } from './studentApiModel'

export interface TaskPermissionInput {
  isLeader: boolean
  taskStatus: TaskStatus
  materialStatus: Material['status']
}

export interface TaskPermission {
  canDraft: boolean
  canSubmit: boolean
  reason: string
}

export function taskPermission(input: TaskPermissionInput): TaskPermission {
  if (input.taskStatus === 'locked') {
    return { canDraft: false, canSubmit: false, reason: '请先完成并通过上一项任务。' }
  }
  if (input.taskStatus === 'pending_review' || input.materialStatus === 'submitted') {
    return { canDraft: false, canSubmit: false, reason: '材料正在等待教师审核。' }
  }
  if (['approved', 'completed'].includes(input.taskStatus) || input.materialStatus === 'approved') {
    return { canDraft: false, canSubmit: false, reason: '材料已通过审核，已作为项目成果归档。' }
  }
  if (input.materialStatus !== 'draft' && input.materialStatus !== 'revision_required') {
    return { canDraft: false, canSubmit: false, reason: '当前材料不可编辑。' }
  }
  return input.isLeader
    ? { canDraft: true, canSubmit: true, reason: '' }
    : { canDraft: true, canSubmit: false, reason: '请由项目负责人确认真实性并正式提交。' }
}
