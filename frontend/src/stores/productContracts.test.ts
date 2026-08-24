import { describe, expect, it } from 'vitest'

import {
  AI_WORKSPACE_MODES,
  JOURNEY_TASK_STATES,
  PROJECT_LIFECYCLE_STATES,
} from './productContracts'

describe('product contracts', () => {
  it('exposes the three approved AI workspace modes', () => {
    expect(AI_WORKSPACE_MODES).toEqual([
      { key: 'opening', label: '开题' },
      { key: 'research', label: '研究' },
      { key: 'defense', label: '答辩' },
    ])
  })

  it('keeps project and journey states explicit', () => {
    expect(PROJECT_LIFECYCLE_STATES).toEqual(['unclaimed', 'active', 'completed', 'archived', 'trashed'])
    expect(JOURNEY_TASK_STATES).toEqual(['available', 'in_progress', 'pending_review', 'revision_required', 'approved', 'completed'])
  })
})
