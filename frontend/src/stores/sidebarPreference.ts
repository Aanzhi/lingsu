export const STUDENT_SIDEBAR_STORAGE_KEY = 'lingsu:student-sidebar-collapsed'

type StorageReader = Pick<Storage, 'getItem'>
type StorageWriter = Pick<Storage, 'setItem'>

export function readSidebarPreference(storage: StorageReader, fallback = true): boolean {
  const value = storage.getItem(STUDENT_SIDEBAR_STORAGE_KEY)
  if (value === '0') return false
  if (value === '1') return true
  return fallback
}

export function writeSidebarPreference(storage: StorageWriter, collapsed: boolean): void {
  storage.setItem(STUDENT_SIDEBAR_STORAGE_KEY, collapsed ? '1' : '0')
}
