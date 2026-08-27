import { describe, expect, it } from 'vitest'
import { readSidebarPreference, writeSidebarPreference } from './sidebarPreference'

describe('sidebar preference', () => {
  it('defaults to collapsed when no preference exists', () => {
    expect(readSidebarPreference({ getItem: () => null })).toBe(true)
  })

  it('restores explicit expanded and collapsed values', () => {
    expect(readSidebarPreference({ getItem: () => '0' })).toBe(false)
    expect(readSidebarPreference({ getItem: () => '1' })).toBe(true)
  })

  it('falls back to collapsed for an invalid value', () => {
    expect(readSidebarPreference({ getItem: () => 'unknown' })).toBe(true)
  })

  it('writes a stable string value for the browser storage adapter', () => {
    let savedKey = ''
    let savedValue = ''
    writeSidebarPreference({ setItem: (key, value) => { savedKey = key; savedValue = value } }, false)
    expect(savedKey).toBe('lingsu:student-sidebar-collapsed')
    expect(savedValue).toBe('0')
  })

  it('writes a stable string value for the expanded browser storage adapter', () => {
    let savedKey = ''
    let savedValue = ''
    writeSidebarPreference({ setItem: (key, value) => { savedKey = key; savedValue = value } }, true)
    expect(savedKey).toBe('lingsu:student-sidebar-collapsed')
    expect(savedValue).toBe('1')
  })
})
