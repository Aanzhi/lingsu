import { computed, reactive, ref } from 'vue'
import { createAnnouncement, createCompetition, createSchool, getAnnouncements, getCompetitions, getSchool, getSchoolAuditEvents, getSchools, resetSchoolInvite, updateCompetition, updateSchool, type Announcement, type AuditEvent, type Competition } from '../api'
import type { ApiSchool } from './platformApiModel'

const state = reactive({ schools: [] as ApiSchool[], competitions: [] as Competition[], announcements: [] as Announcement[] }); const loading = ref(false)
async function load() { loading.value = true; try { const [schools, competitions, announcements] = await Promise.all([getSchools(), getCompetitions(), getAnnouncements()]); state.schools = schools.data; state.competitions = competitions.data; state.announcements = announcements.data } finally { loading.value = false } }
export const platformStore = { state, loading: computed(() => loading.value), load,
  async schoolDetail(id: number) { const [school, auditEvents] = await Promise.all([getSchool(id), getSchoolAuditEvents(id)]); return { school: school.data, auditEvents: auditEvents.data } },
  async createSchool(payload: { name: string; license_expires_at: string | null; is_active: boolean }) { await createSchool(payload); await load() },
  async updateSchool(id: number, payload: Partial<Pick<ApiSchool, 'is_active' | 'license_expires_at' | 'ai_quota' | 'storage_quota_mb'>>) { await updateSchool(id, payload); await load() },
  async resetInvite(id: number) { await resetSchoolInvite(id); await load() },
  async createCompetition(payload: Partial<Competition> & Pick<Competition, 'title'>) { await createCompetition(payload); await load() },
  async toggleCompetition(item: Competition) { await updateCompetition(item.id, { status: item.status === 'published' ? 'draft' : 'published' }); await load() },
  async announce(title: string, body: string) { await createAnnouncement({ title, body, audience: 'all', status: 'published' }); await load() },
}
