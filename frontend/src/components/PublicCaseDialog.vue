<script setup lang="ts">
import { ref } from 'vue'
import { createPublicCase, errorMessage, type PublicCase, resubmitPublicCase } from '../api'
import { makeFeedback, type FeedbackState } from '../stores/feedbackModel'
import FeedbackBanner from './FeedbackBanner.vue'

const props = defineProps<{
  projectId: number
  materials: { id: number; title: string; reportSection: string }[]
  label?: string
  enabled?: boolean
  application?: PublicCase | null
}>()
const emit = defineEmits<{ submitted: [] }>()
const open = ref(false); const busy = ref(false); const error = ref('')
const feedback = ref<FeedbackState | null>(null)
const form = ref({ public_summary: '', tags: '', discipline: '', application_scene: '', outcome_form: '', selected_materials: [] as number[] })
function openDialog() {
  const application = props.application
  form.value = application
    ? { public_summary: application.public_summary, tags: application.tags.join('，'), discipline: application.discipline, application_scene: application.application_scene, outcome_form: application.outcome_form, selected_materials: [...application.selected_materials] }
    : { public_summary: '', tags: '', discipline: '', application_scene: '', outcome_form: '', selected_materials: [] }
  error.value = ''; feedback.value = null; open.value = true
}
async function submit() {
  error.value = ''; feedback.value = null
  if (!form.value.public_summary.trim() || !form.value.selected_materials.length) { error.value = '请填写公开摘要并至少选择一项已通过材料'; feedback.value = makeFeedback('error', error.value, '公开内容必须说明项目摘要，并选择至少一项允许展示的材料。'); return }
  busy.value = true
  try {
    const payload = { project: props.projectId, public_summary: form.value.public_summary, tags: form.value.tags.split(/[,，]/).map((item) => item.trim()).filter(Boolean), discipline: form.value.discipline, application_scene: form.value.application_scene, outcome_form: form.value.outcome_form, selected_materials: form.value.selected_materials }
    if (props.application?.status === 'rejected') await resubmitPublicCase(props.application.id, payload)
    else await createPublicCase(payload)
    open.value = false
    feedback.value = makeFeedback('success', '公开申请已提交。', '主指导教师审核通过前，任何材料都不会对外展示。')
    emit('submitted')
  } catch (reason) { error.value = errorMessage(reason); feedback.value = makeFeedback('error', error.value, '已填写内容仍保留，可以修正后重试。', '重试') } finally { busy.value = false }
}
</script>
<template><FeedbackBanner v-model="feedback" @action="submit" /><button class="secondary-button" :disabled="enabled === false" type="button" @click="openDialog">{{ label ?? '申请公开案例' }}</button><el-dialog v-model="open" :title="application?.status === 'rejected' ? '修改公开申请' : '申请公开案例'" width="640px"><form class="dialog-form" @submit.prevent="submit"><p v-if="error" class="form-error">{{ error }}</p><label>公开摘要<textarea v-model="form.public_summary" rows="4" placeholder="说明问题、方法、关键证据和结论" /></label><div class="form-row"><label>学科<input v-model="form.discipline"></label><label>成果形式<input v-model="form.outcome_form"></label></div><label>应用场景<input v-model="form.application_scene"></label><label>标签<input v-model="form.tags" placeholder="使用逗号分隔"></label><fieldset><legend>允许公开的已通过材料</legend><label v-for="material in materials" :key="material.id" class="truth-check"><input v-model="form.selected_materials" type="checkbox" :value="material.id"><span>{{ material.title }} · {{ material.reportSection }}</span></label></fieldset><div class="dialog-actions"><button class="secondary-button" type="button" @click="open = false">取消</button><button class="primary-button" :disabled="busy" type="submit">{{ busy ? '正在提交…' : application?.status === 'rejected' ? '重新提交教师审核' : '提交教师审核' }}</button></div></form></el-dialog></template>
