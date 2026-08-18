import { describe, expect, it } from 'vitest'

import { publicCaseAction } from './publicCaseModel'

describe('public case action mapping', () => {
  it('only offers a first application after the project is complete and has approved material', () => {
    expect(publicCaseAction({ projectStatus: 'active', approvedMaterialCount: 2, applicationStatus: null })).toEqual({
      enabled: false,
      label: '项目完成后可申请公开',
      reason: '请先完成所有必填任务并通过教师审核。',
    })
    expect(publicCaseAction({ projectStatus: 'completed', approvedMaterialCount: 1, applicationStatus: null })).toEqual({
      enabled: true,
      label: '申请公开案例',
      reason: '',
    })
  })

  it('keeps a rejected request actionable but makes other processed states read-only', () => {
    expect(publicCaseAction({ projectStatus: 'completed', approvedMaterialCount: 1, applicationStatus: 'rejected' })).toEqual({
      enabled: true,
      label: '修改并重新提交',
      reason: '请先根据教师意见修订公开内容。',
    })
    expect(publicCaseAction({ projectStatus: 'completed', approvedMaterialCount: 1, applicationStatus: 'pending_teacher' })).toEqual({
      enabled: false,
      label: '正在等待教师审核',
      reason: '当前申请已提交，无需重复创建。',
    })
  })
})
