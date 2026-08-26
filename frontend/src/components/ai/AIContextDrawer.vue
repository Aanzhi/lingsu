<script setup lang="ts">
import type { AIAgent, Material, Project } from '../../api'
import type { AIWorkspaceMode } from '../../stores/aiWorkbenchModel'

const props = defineProps<{
  open: boolean
  mode: AIWorkspaceMode
  project: Project | null
  materials: Material[]
  agent: AIAgent | null
  paperType?: string
  paperTypes?: Array<{ value: string; label: string }>
  referencedSources?: string[]
  selectedMaterialIds?: number[]
  canSelectMaterials?: boolean
}>()

const emit = defineEmits<{ (event: 'close'): void; (event: 'update-paper-type', value: string): void; (event: 'update:selected-material-ids', value: number[]): void }>()

function toggleMaterial(materialId: number, checked: boolean) {
  const selected = new Set(props.selectedMaterialIds || [])
  if (checked) selected.add(materialId)
  else selected.delete(materialId)
  emit('update:selected-material-ids', [...selected])
}
</script>

<template>
  <Teleport to="body">
  <aside v-if="props.open" id="ai-context-drawer" class="ai-context-drawer" role="dialog" aria-modal="true" aria-label="AI 上下文设置">
    <div class="ai-context-drawer__heading"><div><span class="eyebrow">上下文边界</span><h2>{{ props.mode === 'opening' ? '开题工作区' : '当前项目工作区' }}</h2></div><button type="button" aria-label="关闭上下文设置" @click="emit('close')">×</button></div>
    <div class="ai-context-drawer__context"><span>当前项目</span><strong>{{ props.project?.title || '不绑定项目' }}</strong><small>{{ props.mode === 'opening' ? '开题不会读取或修改任何已有项目。' : '只读取当前项目，不跨项目共享内容。' }}</small></div>
    <dl class="ai-context-drawer__stats"><div><dt>已选材料</dt><dd>{{ props.mode === 'opening' ? 0 : props.selectedMaterialIds?.length || 0 }}</dd></div><div><dt>输出权限</dt><dd>只读草稿</dd></div></dl>
    <div><p class="eyebrow">可读取范围</p><ul><li v-if="props.mode !== 'opening'">项目基本信息和当前任务</li><li v-if="props.mode !== 'opening'">已确认材料、实验日志和教师意见</li><li v-else>你在本次对话中主动提供的观察</li></ul></div>
    <div><p class="eyebrow">当前 Agent</p><p class="ai-context-drawer__agent">{{ props.agent?.name || '自由咨询' }}</p></div>
    <div v-if="props.mode !== 'opening' && props.canSelectMaterials" class="ai-context-drawer__materials">
      <p class="eyebrow">引用材料</p>
      <p class="ai-context-drawer__materials-help">仅选择当前项目中已可读取的材料。发送后会记录实际引用来源。</p>
      <label v-for="material in props.materials" :key="material.id" class="ai-context-drawer__material">
        <input type="checkbox" :checked="props.selectedMaterialIds?.includes(material.id)" @change="toggleMaterial(material.id, ($event.target as HTMLInputElement).checked)" />
        <span>{{ material.title }}</span>
      </label>
      <small v-if="!props.materials.length">当前项目还没有可引用材料。</small>
    </div>
    <label v-if="props.agent?.workflow?.startsWith('paper')" class="ai-context-drawer__paper"><span class="eyebrow">论文类型</span><select :value="props.paperType" @change="emit('update-paper-type', ($event.target as HTMLSelectElement).value)"><option value="">请选择</option><option v-for="item in props.paperTypes || []" :key="item.value" :value="item.value">{{ item.label }}</option></select></label>
    <div v-if="props.referencedSources?.length" class="ai-context-drawer__sources"><p class="eyebrow">本次引用来源</p><span v-for="source in props.referencedSources" :key="source">{{ source }}</span></div>
    <p class="ai-context-drawer__note">AI 生成的内容先作为草稿展示；保存材料、创建项目和提交业务状态都需要你明确确认。</p>
  </aside>
  </Teleport>
</template>

<style scoped>
.ai-context-drawer { position: fixed; top: calc(var(--topbar-height) + 18px); right: 24px; z-index: 100; display: grid; gap: 18px; width: min(340px, calc(100vw - 48px)); max-height: calc(100vh - 104px); overflow-y: auto; padding: 20px; border: 1px solid var(--line-dark); border-radius: var(--radius-md); background: var(--paper); box-shadow: var(--shadow-hover); }
.ai-context-drawer__heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
.ai-context-drawer__heading h2 { margin: 5px 0 0; color: var(--ink); font: 700 18px/1.35 var(--sans); }
.ai-context-drawer__heading button { border: 0; background: transparent; color: var(--muted); font-size: 21px; cursor: pointer; }
.ai-context-drawer__context { display: grid; gap: 5px; padding: 12px; border-radius: var(--radius-sm); background: var(--sage-soft); }
.ai-context-drawer__context span, .ai-context-drawer__context small { color: var(--muted); font-size: 11px; }
.ai-context-drawer__context strong { color: var(--moss-dark); overflow-wrap: anywhere; }
.ai-context-drawer__stats { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0; }
.ai-context-drawer__stats div { padding: 10px; border: 1px solid var(--line); border-radius: var(--radius-sm); }
.ai-context-drawer__stats dt { color: var(--muted); font-size: 11px; }
.ai-context-drawer__stats dd { margin: 5px 0 0; color: var(--ink); font-weight: 700; }
.ai-context-drawer ul { display: grid; gap: 7px; margin: 5px 0 0; padding-left: 17px; color: var(--muted); font-size: 11px; line-height: 1.55; }
.ai-context-drawer__agent { margin: 4px 0 0; color: var(--ink); font-size: 12px; }
.ai-context-drawer__materials { display: grid; gap: 8px; }
.ai-context-drawer__materials-help { margin: 0; color: var(--muted); font-size: 11px; line-height: 1.55; }
.ai-context-drawer__material { display: flex; align-items: center; gap: 8px; padding: 8px; border: 1px solid var(--line); border-radius: var(--radius-sm); color: var(--ink); font-size: 12px; }
.ai-context-drawer__material input { accent-color: var(--moss); }
.ai-context-drawer__paper { display: grid; gap: 6px; }
.ai-context-drawer__paper select { min-height: 32px; border: 1px solid var(--line); border-radius: var(--radius-sm); padding: 6px 8px; background: var(--paper); color: var(--ink); font: inherit; }
.ai-context-drawer__sources { display: grid; gap: 6px; }
.ai-context-drawer__sources span { padding: 6px 8px; border-radius: var(--radius-sm); background: var(--paper-soft); color: var(--muted); font-size: 11px; }
.ai-context-drawer__note { margin: 0; padding-top: 12px; border-top: 1px solid var(--line); color: var(--muted); font-size: 11px; line-height: 1.6; }
</style>
