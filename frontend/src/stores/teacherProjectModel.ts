import type { ApiTask } from './studentApiModel'
import type { Material, Project } from '../api'

export function projectTaskSummary(tasks: ApiTask[]) {
  const total = tasks.length
  const approved = tasks.filter((task) => ['approved', 'completed'].includes(task.status)).length
  const needsReview = tasks.filter((task) => ['pending_review', 'revision_required'].includes(task.status)).length
  return { total, approved, needsReview, percent: total ? Math.round((approved / total) * 100) : 0 }
}

export function projectRiskLabel(tasks: ApiTask[], materials: Material[]) {
  if (tasks.some((task) => task.status === 'revision_required')) return '有材料需要修订'
  if (tasks.some((task) => task.status === 'pending_review')) return '有材料等待审核'
  if (materials.length === 0) return '等待任务材料生成'
  return '当前没有待处理风险'
}

export function teacherProjectHeadline(project: Project, tasks: ApiTask[]) {
  const summary = projectTaskSummary(tasks)
  return `${project.title} · ${summary.approved}/${summary.total} 项任务已通过`
}
