<template>
  <v-app class="app-bg">
    <!-- Sidebar with Gradient -->
    <v-navigation-drawer 
      v-model="drawer" 
      app 
      class="glass-sidebar"
      width="260"
    >
      <div class="pa-6">
        <div class="d-flex align-center gap-3 mb-6">
          <v-avatar color="primary" variant="tonal" rounded="lg" size="48">
            <v-icon icon="mdi-shield-check" size="28"></v-icon>
          </v-avatar>
          <div>
            <div class="text-h6 font-weight-black tracking-tight leading-none text-white">备份大师</div>
            <div class="text-caption text-primary font-weight-bold">Pro Edition</div>
          </div>
        </div>
      </div>

      <v-divider class="mb-2 border-opacity-25"></v-divider>

      <v-list density="comfortable" nav class="px-3">
        <v-list-item 
          to="/" 
          active-class="active-nav-item"
          rounded="lg"
          class="mb-1"
        >
          <template v-slot:prepend>
            <v-icon icon="mdi-view-dashboard-outline"></v-icon>
          </template>
          <v-list-item-title class="font-weight-medium">仪表盘</v-list-item-title>
        </v-list-item>

        <v-list-item 
          to="/history"
          active-class="active-nav-item"
          rounded="lg"
          class="mb-1"
        >
          <template v-slot:prepend>
            <v-icon icon="mdi-history"></v-icon>
          </template>
          <v-list-item-title class="font-weight-medium">历史记录</v-list-item-title>
        </v-list-item>

        <v-list-item 
          to="/explorer"
          active-class="active-nav-item"
          rounded="lg"
          class="mb-1"
        >
          <template v-slot:prepend>
            <v-icon icon="mdi-folder-search-outline"></v-icon>
          </template>
          <v-list-item-title class="font-weight-medium">存储浏览器</v-list-item-title>
        </v-list-item>

        <v-list-item 
          to="/settings"
          active-class="active-nav-item"
          rounded="lg"
          class="mb-1"
        >
          <template v-slot:prepend>
            <v-icon icon="mdi-cog-outline"></v-icon>
          </template>
          <v-list-item-title class="font-weight-medium">系统设置</v-list-item-title>
        </v-list-item>
      </v-list>
      
      <template v-slot:append>
        <div class="pa-4 text-center text-caption text-grey">
          v1.0.0
        </div>
      </template>
    </v-navigation-drawer>

    <!-- Top Bar (Transparent/Glass) -->
    <v-app-bar app height="64" class="glass-header px-2">
      <v-app-bar-nav-icon @click="drawer = !drawer" color="white"></v-app-bar-nav-icon>
      <v-app-bar-title class="text-body-1 font-weight-bold text-grey-lighten-2">
        {{ getPageTitle($route.name) }}
      </v-app-bar-title>
    </v-app-bar>

    <!-- Main Content Area -->
    <v-main>
      <v-container fluid class="pa-6">
        <router-view></router-view>
      </v-container>
    </v-main>

    <!-- Global Dialogs -->
    <CreateProjectDialog />
  </v-app>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import { useUIStore } from './stores/ui'
import CreateProjectDialog from './components/CreateProjectDialog.vue'

const drawer = ref(true)
const route = useRoute()
const uiStore = useUIStore()

const getPageTitle = (name) => {
  const map = {
    'Dashboard': '系统概览',
    'History': '任务日志',
    'GlobalHistory': '系统日志中心',
    'Explorer': '存储浏览器',
    'Settings': '系统设置'
  }
  return map[name] || '系统概览'
}
</script>

<style>
/* Global Styles for Deep Ocean Theme */
:root {
  --v-theme-background: #020617;
}

body {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  background-color: #020617; /* Ensure body matches theme background */
}

.app-bg {
  background-color: #020617 !important;
}

/* Glassmorphism Sidebar */
.glass-sidebar {
  background: linear-gradient(180deg, #0f172a 0%, #020617 100%) !important;
  border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Glass Header */
.glass-header {
  background: rgba(2, 6, 23, 0.8) !important;
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
}

/* Navigation Item Styling */
.active-nav-item {
  background: rgba(129, 140, 248, 0.15) !important; /* Primary color with low opacity */
  color: #818cf8 !important; /* Primary text */
}

.tracking-tight { letter-spacing: -0.025em; }
.leading-none { line-height: 1; }
.gap-3 { gap: 12px; }
</style>
