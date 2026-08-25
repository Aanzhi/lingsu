import { computed, ref } from 'vue'

import { getCsrf, getMe, login as loginRequest, logout as logoutRequest, registerAccount, type MeResponse } from '../api'
import type { AuthRole, AuthUser } from './authModel'

const user = ref<AuthUser | null>(null)
const initialized = ref(false)
const loading = ref(false)

function mapUser(data: MeResponse): AuthUser {
  return {
    id: data.id, username: data.username, displayName: data.display_name || data.username,
    role: data.role, school: data.school, schoolName: data.school_name,
    authorized: data.authorized, mustChangePassword: data.must_change_password,
    primaryProject: data.primary_project, primaryProjectTitle: data.primary_project_title,
  }
}

async function restore() {
  if (initialized.value) return user.value
  try {
    const session = (await getMe()).data
    if ('authenticated' in session && session.authenticated === false) user.value = null
    else user.value = mapUser(session as MeResponse)
  } catch { user.value = null }
  initialized.value = true
  return user.value
}

export const auth = {
  user: computed(() => user.value), initialized: computed(() => initialized.value), loading: computed(() => loading.value),
  restore,
  async login(username: string, password: string) {
    loading.value = true
    try { await getCsrf(); user.value = mapUser((await loginRequest(username, password)).data); initialized.value = true; return user.value }
    finally { loading.value = false }
  },
  async register(payload: { invite_code: string; role: 'student' | 'teacher'; username: string; password: string; display_name: string }) {
    loading.value = true
    try { await getCsrf(); user.value = mapUser((await registerAccount(payload)).data); initialized.value = true; return user.value }
    finally { loading.value = false }
  },
  async logout() {
    try { await logoutRequest() } catch { /* local sign-out must still complete if the session already expired */ }
    finally { user.value = null; initialized.value = true }
  },
  setForTest(next: AuthUser | null) { user.value = next; initialized.value = true },
  resetInitialization() { user.value = null; initialized.value = false },
  role: computed<AuthRole | null>(() => user.value?.role ?? null),
}
