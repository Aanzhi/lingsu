import type { Project, PublicCase } from '../api'

interface PublicCaseActionInput {
  projectStatus: Project['status']
  approvedMaterialCount: number
  applicationStatus: PublicCase['status'] | null
}

export function publicCaseAction(input: PublicCaseActionInput) {
  if (input.applicationStatus === 'rejected') {
    return { enabled: true, label: '修改并重新提交', reason: '请先根据教师意见修订公开内容。' }
  }
  if (input.applicationStatus === 'pending_teacher') {
    return { enabled: false, label: '正在等待教师审核', reason: '当前申请已提交，无需重复创建。' }
  }
  if (input.applicationStatus === 'published') {
    return { enabled: false, label: '案例已公开', reason: '公开内容已进入案例库。' }
  }
  if (input.applicationStatus === 'offline') {
    return { enabled: false, label: '案例已下架', reason: '请联系平台管理员处理治理状态。' }
  }
  if (input.projectStatus !== 'completed') {
    return { enabled: false, label: '项目完成后可申请公开', reason: '请先完成所有必填任务并通过教师审核。' }
  }
  if (!input.approvedMaterialCount) {
    return { enabled: false, label: '暂无可公开材料', reason: '至少需要一项已通过材料。' }
  }
  return { enabled: true, label: '申请公开案例', reason: '' }
}
