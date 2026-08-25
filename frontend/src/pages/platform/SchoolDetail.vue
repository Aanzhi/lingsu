<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { CopyDocument, Refresh, Setting } from '@element-plus/icons-vue'
import type { ApiSchool } from '../../stores/platformApiModel'
import type { AuditEvent } from '../../api'
import { errorMessage } from '../../api'
import ConfirmDialog from '../../components/ConfirmDialog.vue'
import EmptyState from '../../components/EmptyState.vue'
import FeedbackBanner from '../../components/FeedbackBanner.vue'
import PageHeader from '../../components/PageHeader.vue'
import StatusTag from '../../components/StatusTag.vue'
import { makeFeedback, type FeedbackState } from '../../stores/feedbackModel'
import { auditEventMessage, makeSchoolConfigurationDraft, schoolConfigurationChanges } from '../../stores/platformDetailModel'
import { platformStore } from '../../stores/platform'

const route = useRoute()
const schoolId = computed(() => Number(route.params.id))
const school = ref<ApiSchool | null>(null)
const auditEvents = ref<AuditEvent[]>([])
const loading = ref(true)
const saving = ref(false)
const feedback = ref<FeedbackState | null>(null)
const confirmReset = ref(false)
const advancedOpen = ref(false)
const auditPage = ref(1)
const auditPageSize = 5
const auditTotalPages = computed(() => Math.max(1, Math.ceil(auditEvents.value.length / auditPageSize)))
const visibleAuditEvents = computed(() => auditEvents.value.slice((auditPage.value - 1) * auditPageSize, auditPage.value * auditPageSize))
const form = reactive({ license_expires_at: null as string | null, ai_quota: 0, storage_quota_mb: 0 })

function assignForm(value: ApiSchool) { Object.assign(form, makeSchoolConfigurationDraft(value)) }
async function load() {
  loading.value = true
  try {
    const result = await platformStore.schoolDetail(schoolId.value)
    school.value = result.school
    auditEvents.value = result.auditEvents
    auditPage.value = 1
    assignForm(result.school)
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '学校详情没有加载完成，可以重试。', '重新加载')
  } finally { loading.value = false }
}
async function save() {
  if (!school.value) return
  const changes = schoolConfigurationChanges(school.value, form)
  if (!Object.keys(changes).length) {
    feedback.value = makeFeedback('info', '没有需要保存的配置变更。')
    return
  }
  saving.value = true
  try {
    await platformStore.updateSchool(school.value.id, changes)
    await load()
    feedback.value = makeFeedback('success', '学校配置已保存。', '授权期限与配额已更新，并写入操作记录。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '未保存的表单内容仍保留，可以修正后重试。', '重新保存')
  } finally { saving.value = false }
}
async function resetInvite() {
  if (!school.value) return
  confirmReset.value = false
  saving.value = true
  try {
    await platformStore.resetInvite(school.value.id)
    await load()
    feedback.value = makeFeedback('success', '学校邀请码已重置。', '旧邀请码已立即失效，请仅通过安全渠道发送新邀请码。')
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '邀请码没有重置，请确认后再次操作。')
  } finally { saving.value = false }
}
async function copyInvite() {
  if (!school.value) return
  try {
    await navigator.clipboard.writeText(school.value.invite_code)
    feedback.value = makeFeedback('success', '邀请码已复制到剪贴板。', '请仅通过安全渠道发送给学校。')
  } catch { feedback.value = makeFeedback('error', '浏览器未允许复制。', '请手动选择邀请码复制。') }
}
async function handleFeedbackAction() {
  if (feedback.value?.actionLabel === '重新保存') await save()
  else await load()
}
onMounted(load)
watch(schoolId, () => {
  confirmReset.value = false
  feedback.value = null
  void load()
})
watch(auditTotalPages, (value) => { if (auditPage.value > value) auditPage.value = value })
watch(advancedOpen, (value) => {
  if (!value) return
  requestAnimationFrame(() => { const details = document.querySelector<HTMLDetailsElement>('.school-advanced'); if (details) details.open = true })
})
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="学校详情" :title="school?.name ?? '学校详情'" description="查看该学校的成员、项目、邀请码和服务配额。"> <template #actions><RouterLink class="secondary-button" to="/platform/schools">返回学校列表</RouterLink></template></PageHeader>
    <FeedbackBanner v-model="feedback" @action="handleFeedbackAction" />
    <p v-if="loading" class="loading-state" role="status">正在读取学校详情…</p>
    <template v-if="school">
      <section class="pilot-metric-grid school-metric-grid" aria-label="学校空间指标">
        <article class="pilot-card pilot-metric"><div class="pilot-metric__label">活跃项目</div><div class="pilot-metric__value">{{ school.project_count }}</div><div class="pilot-metric__foot">当前学校空间</div></article>
        <article class="pilot-card pilot-metric"><div class="pilot-metric__label">学生</div><div class="pilot-metric__value">{{ school.student_count }}</div><div class="pilot-metric__foot">已授权账号</div></article>
        <article class="pilot-card pilot-metric"><div class="pilot-metric__label">指导教师</div><div class="pilot-metric__value">{{ school.teacher_count }}</div><div class="pilot-metric__foot">本学期活跃</div></article>
        <article class="pilot-card pilot-metric"><div class="pilot-metric__label">空间状态</div><div class="pilot-metric__value school-status-value">{{ school.is_authorized ? '已启用' : '只读' }}</div><div class="pilot-metric__foot good">{{ school.is_authorized ? '服务正常' : '历史数据可浏览' }}</div></article>
      </section>
      <section class="demo-school-info-grid"><article class="paper-card"><h2>学校信息</h2><div class="demo-school-info-list"><div><span>联系人</span><strong>{{ school.teacher_count }} 位教师</strong></div><div><span>邀请码</span><span class="chip">{{ school.invite_code }}</span></div><div><span>授权到期</span><span class="muted">{{ school.license_expires_at || '长期有效' }}</span></div></div></article><article class="paper-card"><h2>空间操作</h2><p class="muted">授权开关只影响访问，不会删除学校数据或项目内容。</p><div class="demo-school-actions"><button class="primary-button" type="button" @click="advancedOpen = true">管理授权</button><button class="secondary-button" type="button" @click="copyInvite">复制邀请码</button></div></article></section>
      <details class="school-advanced"><summary>高级配置与操作记录</summary><section class="paper-card configuration-panel"><div class="section-heading"><div><p class="eyebrow">可写配置</p><h2>授权与学校配额</h2></div><el-icon><Setting /></el-icon></div><form class="configuration-form" @submit.prevent="save"><label>授权到期日<input v-model="form.license_expires_at" type="date"><small>留空表示长期有效。</small></label><label>AI 月度配额（次）<input v-model.number="form.ai_quota" min="0" type="number"><small>配额不足时，AI 生成功能会明确提示。</small></label><label>存储配额（MB）<input v-model.number="form.storage_quota_mb" min="1" type="number"><small>材料上传将按学校总额校验。</small></label><footer><span>保存后会影响该学校后续写入能力，不会删除任何历史项目。</span><button class="primary-button" :disabled="saving" type="submit">{{ saving ? '正在保存…' : '保存配置' }}</button></footer></form></section><section class="paper-card audit-panel"><div class="section-heading"><div><p class="eyebrow">治理记录</p><h2>最近操作</h2></div><span>{{ auditEvents.length }} 条</span></div><div v-for="event in visibleAuditEvents" :key="event.id" class="audit-row"><span class="audit-dot" /><div><strong>{{ auditEventMessage(event) }}</strong><small>{{ event.actor_name }} · {{ event.created_at.slice(0, 16).replace('T', ' ') }}</small></div></div><EmptyState v-if="!auditEvents.length && !loading" title="暂无操作记录" description="修改学校配置或重置邀请码后，记录会出现在这里。" /><nav v-if="auditEvents.length > auditPageSize" class="audit-pagination" aria-label="操作记录分页"><button class="secondary-button" type="button" :disabled="auditPage === 1" @click="auditPage -= 1">上一页</button><span>第 {{ auditPage }} / {{ auditTotalPages }} 页</span><button class="secondary-button" type="button" :disabled="auditPage === auditTotalPages" @click="auditPage += 1">下一页</button></nav></section></details>
    </template>
    <EmptyState v-else-if="!loading" title="学校详情不可用" description="请返回学校空间确认该学校是否存在。" />
    <ConfirmDialog v-if="confirmReset" :model-value="true" title="重置学校邀请码？" description="旧邀请码会立即失效，尚未注册的师生需要使用新邀请码。" confirm-text="确认重置" danger @update:model-value="confirmReset = false" @confirm="resetInvite" />
  </div>
</template>

<style scoped>
.school-metric-grid { margin-bottom: 17px; }
.school-status-value { font-size: 25px; }
.demo-school-info-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; }
.demo-school-info-grid > article { padding: 26px; }
.demo-school-info-grid h2 { margin: 0 0 14px; font-size: 20px; }
.demo-school-info-list { display: grid; }
.demo-school-info-list > div { display: flex; min-height: 48px; align-items: center; justify-content: space-between; gap: 16px; border-top: 1px solid var(--line); font-size: 12px; }
.demo-school-info-list > div:first-child { border-top: 0; }
.demo-school-actions { display: grid; gap: 9px; margin-top: 16px; }
.demo-school-actions > * { width: 100%; justify-content: center; box-sizing: border-box; }
.school-advanced { margin-top: 18px; }
.school-advanced > summary { width: fit-content; cursor: pointer; color: var(--muted); font-size: 12px; font-weight: 700; }
.school-advanced[open] > summary { margin-bottom: 14px; }
.school-advanced .configuration-panel, .school-advanced .audit-panel { margin-top: 14px; }
.audit-pagination { display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 16px; color: var(--muted); font-size: 12px; }
</style>
