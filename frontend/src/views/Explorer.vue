<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-avatar color="info" variant="tonal" class="mr-4" rounded>
        <v-icon icon="mdi-folder-search-outline"></v-icon>
      </v-avatar>
      <div>
        <h2 class="text-h5 font-weight-bold text-white">存储浏览器</h2>
        <div class="text-caption text-grey">
          查看服务器映射路径的物理文件情况
          <v-chip size="x-small" color="success" variant="tonal" class="ml-2">
            <v-icon start icon="mdi-lightning-bolt" size="x-small"></v-icon>极致性能模式
          </v-chip>
        </div>
      </div>
    </div>

    <v-alert type="warning" variant="tonal" density="compact" class="mb-4 text-caption" icon="mdi-shield-check">
      <b>安全提示：</b> 存储浏览器仅读取<b>文件列表和元数据</b>（名称、大小），<b>绝不读取</b>文件实际内容。
      在挂载网盘（CloudDrive2/Rclone）上使用时，不会触发文件下载，API 开销极低。
    </v-alert>

    <!-- Navigation Card -->
    <v-card class="border-glow bg-surface overflow-hidden">
      <!-- Breadcrumbs / Path bar -->
      <v-toolbar color="surface-light" density="comfortable" flat class="border-b">
        <v-btn icon="mdi-home" variant="text" size="small" @click="fetchDir('/')"></v-btn>
        <v-divider vertical class="mx-2"></v-divider>
        <div class="d-flex align-center px-2 overflow-x-auto no-scrollbar" style="max-width: 80%;">
          <v-chip
            v-for="(part, i) in pathParts"
            :key="i"
            size="small"
            variant="text"
            class="px-1 text-grey-lighten-1"
            @click="navigateToPart(i)"
          >
            {{ part }}
            <template v-if="i < pathParts.length - 1">
              <v-icon size="x-small" class="ml-1">mdi-chevron-right</v-icon>
            </template>
          </v-chip>
        </div>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-refresh" variant="text" size="small" @click="fetchDir(currentPath)" :loading="loading"></v-btn>
      </v-toolbar>

      <v-card-text class="pa-0">
        <v-list density="comfortable" class="pa-0 bg-surface">
          <!-- Table Header (Simulation) -->
          <v-list-item class="bg-black border-b py-1" style="min-height: 32px;">
            <v-row no-gutters class="text-caption font-weight-bold text-grey">
              <v-col cols="7">名称</v-col>
              <v-col cols="2">大小</v-col>
              <v-col cols="3" class="text-right">类型</v-col>
            </v-row>
          </v-list-item>

          <div v-if="loading && items.length === 0" class="pa-12 text-center">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </div>

          <template v-else>
            <v-list-item
              v-for="item in items"
              :key="item.path"
              @click="navigate(item)"
              class="border-b explorer-item"
              :ripple="true"
              :class="{ 'mapped-path-active': item.is_mount }"
            >
              <v-row no-gutters align="center">
                <v-col cols="7" class="d-flex align-center">
                  <v-icon 
                    :icon="item.is_dir ? (item.is_mount ? 'mdi-harddisk' : 'mdi-folder') : 'mdi-file-outline'" 
                    :color="item.is_mount ? 'primary' : (item.is_dir ? 'info' : 'grey')" 
                    class="mr-3"
                  ></v-icon>
                  <span class="text-body-2 font-weight-medium text-white truncate-text">
                    {{ item.name }}
                    <v-chip v-if="item.is_mount" size="x-small" color="primary" class="ml-2" variant="flat">核心挂载点</v-chip>
                  </span>
                </v-col>
                <v-col cols="2">
                  <span class="text-caption text-grey">{{ item.is_dir ? '-' : formatSize(item.size) }}</span>
                </v-col>
                <v-col cols="3" class="text-right">
                  <v-chip size="x-small" variant="tonal" :color="item.is_dir ? 'info' : 'grey-darken-1'">
                    {{ item.is_dir ? '文件夹' : '文件' }}
                  </v-chip>
                </v-col>
              </v-row>
            </v-list-item>

            <v-list-item v-if="items.length === 0" class="pa-12 text-center text-grey">
              <v-icon size="48" color="grey-darken-3">mdi-folder-open-outline</v-icon>
              <div class="mt-2">此目录为空</div>
            </v-list-item>
          </template>
        </v-list>
      </v-card-text>
    </v-card>

    <div class="mt-4 text-caption text-grey-darken-1 d-flex align-center">
      <v-icon icon="mdi-information-outline" size="small" class="mr-1"></v-icon>
      提示：您可以点击文件夹进行跳转，浏览器仅显示容器内可见的映射路径。
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'

const currentPath = ref('/')
const items = ref([])
const loading = ref(false)

const pathParts = computed(() => {
  if (currentPath.value === '/') return ['root']
  return ['root', ...currentPath.value.split('/').filter(p => p !== '')]
})

const navigateToPart = (index) => {
  if (index === 0) {
    fetchDir('/')
    return
  }
  const parts = currentPath.value.split('/').filter(p => p !== '')
  const targetPath = '/' + parts.slice(0, index).join('/')
  fetchDir(targetPath)
}

const fetchDir = async (path) => {
  loading.value = true
  try {
    const res = await axios.get('/api/system/browse', { params: { path } })
    items.value = res.data
    currentPath.value = path
  } catch (err) {
    console.error("Browse failed", err)
  } finally {
    loading.value = false
  }
}

const navigate = (item) => {
  if (item.is_dir) {
    fetchDir(item.path)
  }
}

const formatSize = (bytes) => {
  if (bytes === 0) return '0 B'
  if (!bytes) return '-'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  if (i < 0) return bytes + ' B'
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

onMounted(() => {
  fetchDir('/')
})
</script>

<style scoped>
.border-glow { border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 0 30px rgba(0,0,0,0.3); }
.border-b { border-bottom: 1px solid rgba(255,255,255,0.05) !important; }
.bg-surface-light { background-color: #1e293b !important; }
.explorer-item:hover {
  background-color: rgba(255, 255, 255, 0.03) !important;
}
.truncate-text {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 400px;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
</style>
