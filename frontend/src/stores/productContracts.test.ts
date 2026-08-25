import { describe, expect, expectTypeOf, it, vi } from 'vitest'

import {
  api,
  createAIConversation,
  getProjectTasks,
  updateAIConversation,
  type Project,
  type ProjectTask,
} from '../api'

import {
  AI_WORKSPACE_MODES,
  JOURNEY_TASK_STATES,
  PROJECT_LIFECYCLE_STATES,
  type JourneyTaskState,
  type ProjectLifecycleState,
} from './productContracts'

describe('product contracts', () => {
  it('exposes the three approved AI workspace modes', () => {
    expect(AI_WORKSPACE_MODES).toEqual([
      { key: 'opening', label: '开题' },
      { key: 'research', label: '研究' },
      { key: 'defense', label: '成果表达' },
    ])
  })

  it('keeps project and journey states explicit', () => {
    expect(PROJECT_LIFECYCLE_STATES).toEqual(['unclaimed', 'active', 'completed', 'archived', 'trashed'])
    expect(JOURNEY_TASK_STATES).toEqual(['available', 'in_progress', 'pending_review', 'revision_required', 'approved', 'completed'])
  })

  it('aligns project and task status types with the shared contracts', () => {
    expectTypeOf<Project['status']>().toEqualTypeOf<ProjectLifecycleState>()
    expectTypeOf<ProjectTask['status']>().toEqualTypeOf<JourneyTaskState>()
  })

  it('keeps null fields when creating and updating AI conversations', async () => {
    const post = vi.spyOn(api, 'post').mockResolvedValue({} as never)
    const patch = vi.spyOn(api, 'patch').mockResolvedValue({} as never)

    await createAIConversation({ project: null, current_agent: null })
    await updateAIConversation(4, { paper_type: null })

    expect(post).toHaveBeenCalledWith('ai-conversations/', { project: null, current_agent: null })
    expect(patch).toHaveBeenCalledWith('ai-conversations/4/', { paper_type: null })

    post.mockRestore()
    patch.mockRestore()
  })

  it('normalizes legacy locked project tasks at the API boundary', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({
      data: [
        {
          id: 1,
          project: 9,
          stage_name: '立项与开题',
          stage_order: 1,
          title: '选题',
          description: '完成选题确认',
          evidence_requirements: [],
          order: 1,
          status: 'locked',
          xp_reward: 100,
          due_at: null,
        },
        {
          id: 2,
          project: 9,
          stage_name: '立项与开题',
          stage_order: 1,
          title: '查新',
          description: '完成查新记录',
          evidence_requirements: [],
          order: 2,
          status: 'pending_review',
          xp_reward: 100,
          due_at: null,
        },
      ],
      status: 200,
      statusText: 'OK',
      headers: {},
      config: {},
    } as never)

    const response = await getProjectTasks(9)

    expect(get).toHaveBeenCalledWith('project-tasks/', { params: { project: 9 } })
    expect(response.data).toEqual([
      {
        id: 1,
        project: 9,
        stage_name: '立项与开题',
        stage_order: 1,
        title: '选题',
        description: '完成选题确认',
        evidence_requirements: [],
        order: 1,
        status: 'available',
        legacy_status: 'locked',
        xp_reward: 100,
        due_at: null,
      },
      {
        id: 2,
        project: 9,
        stage_name: '立项与开题',
        stage_order: 1,
        title: '查新',
        description: '完成查新记录',
        evidence_requirements: [],
        order: 2,
        status: 'pending_review',
        legacy_status: null,
        xp_reward: 100,
        due_at: null,
      },
    ])

    get.mockRestore()
  })
})
