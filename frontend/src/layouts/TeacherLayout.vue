<script setup lang="ts">
import type { Component } from 'vue'
import { Briefcase, ChatLineSquare, Collection, DocumentChecked, FolderOpened, House, Medal, Reading } from '@element-plus/icons-vue'
import { RouterLink, RouterView } from 'vue-router'
import AppTopbar from '../components/AppTopbar.vue'
const nav: [string, string, Component][] = [
  ['/teacher/home', '工作台', House], ['/teacher/pool', '项目池', Collection], ['/teacher/projects', '指导项目', FolderOpened],
  ['/teacher/reviews', '材料审核', DocumentChecked], ['/teacher/members', '成员确认', Briefcase], ['/teacher/ai', '审核 AI', ChatLineSquare],
  ['/teacher/cases', '案例审核', Reading], ['/teacher/competitions', '赛事信息', Medal], ['/teacher/announcements', '通知公告', Reading],
]
</script>
<template><div class="portal teacher-portal"><AppTopbar role-label="教师端" role-tone="teacher" /><div class="desk-shell"><aside class="side-nav"><p>指导工作台</p><RouterLink v-for="item in nav" :key="item[0]" :to="item[0]"><el-icon><component :is="item[2]" /></el-icon><span>{{ item[1] }}</span></RouterLink></aside><main class="desk-main"><RouterView /></main></div></div></template>
