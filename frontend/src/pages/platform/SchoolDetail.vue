<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
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
const form = reactive({ license_expires_at: null as string | null, ai_quota: 0, storage_quota_mb: 0 })

function assignForm(value: ApiSchool) { Object.assign(form, makeSchoolConfigurationDraft(value)) }
async function load() {
  loading.value = true
  try {
    const result = await platformStore.schoolDetail(schoolId.value)
    school.value = result.school
    auditEvents.value = result.auditEvents
    assignForm(result.school)
  } catch (reason) {
    feedback.value = makeFeedback('error', errorMessage(reason), '学校详情没有加载完成，可以重试。', '重试')
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
    feedback.value = makeFeedback('error', errorMessage(reason), '未保存的表单内容仍保留，可以修正后重试。', '重试')
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
    feedback.value = makeFeedback('error', errorMessage(reason), '邀请码没有重置，可以重试。', '重试')
  } finally { saving.value = false }
}
async function copyInvite() {
  if (!school.value) return
  try {
    await navigator.clipboard.writeText(school.value.invite_code)
    feedback.value = makeFeedback('success', '邀请码已复制到剪贴板。', '请仅通过安全渠道发送给学校。')
  } catch { feedback.value = makeFeedback('error', '浏览器未允许复制。', '请手动选择邀请码复制。') }
}
onMounted(load)
</script>

<template>
  <div class="page platform-page">
    <PageHeader eyebrow="学校空间" :title="school?.name ?? '学校详情'" description="在这里集中维护学校授权、邀请码、AI 与存储配额；每次保存都会保留不含敏感值的操作记录。" />
    <FeedbackBanner v-model="feedback" @action="feedback?.actionLabel === '重试' ? load() : save()" />
    <template v-if="school">
      <section class="school-summary-grid">
        <article class="paper-card school-license-card"><p class="eyebrow">当前授权</p><StatusTag :status="school.is_authorized ? 'active' : 'disabled'" /><h2>{{ school.is_authorized ? '学校可以正常写入' : '学校当前为历史只读' }}</h2><p>授权到期：{{ school.license_expires_at || '长期有效' }}</p></article>
        <article class="paper-card school-license-card"><div class="section-heading"><div><p class="eyebrow">学校邀请码</p><h2>{{ school.invite_code }}</h2></div><button class="icon-button" type="button" aria-label="复制学校邀请码" @click="copyInvite"><el-icon><CopyDocument /></el-icon></button></div><p>学生与教师注册时使用。重置后旧邀请码将立即失效。</p><button class="secondary-button" :disabled="saving" type="button" @click="confirmReset = true"><el-icon><Refresh /></el-icon> 重置邀请码</button></article>
      </section>
      <section class="paper-card configuration-panel"><div class="section-heading"><div><p class="eyebrow">可写配置</p><h2>授权与学校配额</h2></div><el-icon><Setting /></el-icon></div><form class="configuration-form" @submit.prevent="save"><label>授权到期日<input v-model="form.license_expires_at" type="date"><small>留空表示长期有效。</small></label><label>AI 月度配额（次）<input v-model.number="form.ai_quota" min="0" type="number"><small>配额不足时，AI 生成功能会明确提示。</small></label><label>存储配额（MB）<input v-model.number="form.storage_quota_mb" min="1" type="number"><small>材料上传将按学校总额校验。</small></label><footer><span>保存后会影响该学校后续写入能力，不会删除任何历史项目。</span><button class="primary-button" :disabled="saving" type="submit">{{ saving ? '正在保存…' : '保存配置' }}</button></footer></form></section>
      <section class="paper-card audit-panel"><div class="section-heading"><div><p class="eyebrow">治理记录</p><h2>最近操作</h2></div><span>{{ auditEvents.length }} 条</span></div><div v-for="event in auditEvents" :key="event.id" class="audit-row"><span class="audit-dot" /><div><strong>{{ auditEventMessage(event) }}</strong><small>{{ event.actor_name }} · {{ event.created_at.slice(0, 16).replace('T', ' ') }}</small></div></div><EmptyState v-if="!auditEvents.length && !loading" title="暂无操作记录" description="修改学校配置或重置邀请码后，记录会出现在这里。" /></section>
    </template>
    <EmptyState v-else-if="!loading" title="学校详情不可用" description="请返回学校空间确认该学校是否存在。" />
    <ConfirmDialog v-if="confirmReset" :model-value="true" title="重置学校邀请码？" description="旧邀请码会立即失效，尚未注册的师生需要使用新邀请码。" confirm-text="确认重置" danger @update:model-value="confirmReset = false" @confirm="resetInvite" />
  </div>
</template>
