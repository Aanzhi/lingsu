<script setup lang="ts">
import { computed } from 'vue'

export interface JourneyKpi {
  label: string
  value: string | number
  caption: string
}

const props = defineProps<{
  kpis: JourneyKpi[]
  title?: string
  subtitle?: string
  level?: number
  levelTitle?: string
  totalXp?: number
}>()

const kpiEntries = computed(() => props.kpis.slice(0, 4))
</script>

<template>
  <section class="paper-card journey-hero">
    <div class="hero-top">
      <div class="journey-hero__heading">
        <p v-if="title" class="eyebrow">{{ title }}</p>
        <h2>把项目拆成几个真实阶段，一关一关走过来</h2>
        <p v-if="subtitle" class="journey-hero__sub">{{ subtitle }}</p>
        <ul v-if="kpiEntries.length" class="journey-hero__kpis">
          <li v-for="kpi in kpiEntries" :key="kpi.label">
            <small>{{ kpi.label }}</small>
            <strong>{{ kpi.value }}</strong>
            <span>{{ kpi.caption }}</span>
          </li>
        </ul>
      </div>
      <div v-if="level" class="level-seal">
        <span>Lv.{{ level }}</span>
        <small v-if="levelTitle">{{ levelTitle }}</small>
        <small v-else>研究等级</small>
        <small v-if="totalXp" class="level-seal__xp">{{ totalXp }} XP</small>
      </div>
    </div>
    <slot />
  </section>
</template>

<style scoped>
.journey-hero__heading { display: flex; flex-direction: column; gap: 8px; max-width: 760px; }
.journey-hero__sub { color: var(--muted); font-size: 13px; max-width: 620px; line-height: 1.65; margin: 0; }
.journey-hero__kpis {
  list-style: none;
  margin: 18px 0 0;
  padding: 0;
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.journey-hero__kpis li {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px 9px;
  background: var(--sage-soft);
  border: 1px solid #c8d8c0;
  border-radius: 999px;
  color: var(--moss-dark);
}
.journey-hero__kpis li small {
  font-size: 10px;
  letter-spacing: .08em;
  color: var(--moss);
  font-weight: 700;
  text-transform: uppercase;
}
.journey-hero__kpis li strong {
  font: 700 16px/1 var(--serif);
  color: var(--moss-dark);
}
.journey-hero__kpis li span { font-size: 11.5px; color: var(--moss); }

.level-seal { position: relative; }
.level-seal__xp {
  position: absolute;
  bottom: -14px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  font-weight: 700;
  color: var(--moss-dark);
  background: var(--paper);
  padding: 2px 8px;
  border: 1px solid var(--sage);
  border-radius: 999px;
  white-space: nowrap;
}

@media (max-width: 720px) {
  .journey-hero__kpis li { flex: 1 1 calc(50% - 5px); justify-content: flex-start; }
}
</style>
