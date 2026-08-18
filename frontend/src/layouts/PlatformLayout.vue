<script setup lang="ts">
import type { Component } from 'vue'
import { Bell, Collection, Files, House, Medal, Setting } from '@element-plus/icons-vue'
import { RouterLink, RouterView } from 'vue-router'
import AppTopbar from '../components/AppTopbar.vue'
const nav: [string, string, Component][] = [
  ['/platform/home', '平台概览', House], ['/platform/schools', '学校空间', Collection],
  ['/platform/competitions', '赛事管理', Medal], ['/platform/announcements', '系统公告', Bell], ['/platform/cases', '案例治理', Files], ['/platform/settings', '平台设置', Setting],
]
</script>
<template><div class="portal platform-portal"><AppTopbar role-label="平台端" role-tone="platform" /><div class="console-shell"><aside class="side-nav platform-nav"><p>开发公司控制台</p><RouterLink v-for="item in nav" :key="item[0]" :to="item[0]"><el-icon><component :is="item[2]" /></el-icon><span>{{ item[1] }}</span></RouterLink></aside><main class="console-main"><RouterView /></main></div></div></template>
