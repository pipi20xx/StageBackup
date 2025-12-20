<template>
  <div>
    <div class="d-flex align-center mb-6">
      <v-btn icon="mdi-arrow-left" variant="text" to="/" class="mr-4"></v-btn>
      <div>
        <h2 class="text-h5 font-weight-bold">备份历史记录</h2>
        <div class="text-caption text-grey">项目 ID: {{ route.params.id }}</div>
      </div>
    </div>

    <v-card :loading="loading">
      <v-table>
        <thead>
          <tr>
            <th class="text-left">状态</th>
            <th class="text-left">开始时间</th>
            <th class="text-left">耗时</th>
            <th class="text-left">文件大小</th>
            <th class="text-left">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="record in history" :key="record.id">
            <td>
              <v-chip
                :color="getStatusColor(record.status)"
                size="small"
                variant="flat"
                class="font-weight-bold"
              >
                {{ getStatusText(record.status) }}
              </v-chip>
            </td>
            <td class="text-grey-lighten-1">{{ formatDate(record.start_time) }}</td>
            <td>{{ calculateDuration(record.start_time, record.end_time) }}</td>
            <td class="font-weight-medium">{{ formatSize(record.file_size_bytes) }}</td>
            <td>
              <v-btn size="small" variant="text" color="primary" @click="showLog(record)">
                查看日志
              </v-btn>
            </td>
          </tr>
          <tr v-if="history.length === 0 && !loading">
            <td colspan="5" class="text-center py-8 text-grey">暂无运行记录</td>
          </tr>
        </tbody>
      </v-table>
    </v-card>

    <!-- Log Dialog -->
    <v-dialog v-model="logDialog" max-width="900" scrollable>
      <v-card color="background" class="border-glow shadow-24">
        <v-card-title class="d-flex justify-space-between align-center pa-4 bg-black border-b">
          <span class="text-subtitle-1 font-weight-bold text-white">详细日志</span>
          <v-btn icon="mdi-close" variant="text" size="small" color="grey" @click="logDialog = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-0 bg-black">
           <pre class="pa-6 font-weight-mono text-body-2 text-grey-lighten-1 log-container">{{ selectedLog }}</pre>
        </v-card-text>
        <v-card-actions class="bg-black pa-4 border-t">
          <v-spacer></v-spacer>
          <v-btn variant="flat" color="primary" @click="logDialog = false" class="px-6">关闭</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const history = ref([])
const loading = ref(false)
const logDialog = ref(false)
const selectedLog = ref('')

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/api/projects/${route.params.id}/history`)
    history.value = res.data
  } catch (err) {
    console.error(err)
  } finally {
    loading.value = false
  }
}

const getStatusColor = (status) => {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'error'
  return 'info'
}

const getStatusText = (status) => {
  if (status === 'success') return '成功'
  if (status === 'failed') return '失败'
  if (status === 'running') return '运行中'
  return status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

const calculateDuration = (start, end) => {
  if (!start || !end) return '-'
  const diff = new Date(end) - new Date(start)
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}秒`
  return `${Math.floor(seconds / 60)}分 ${seconds % 60}秒`
}

const formatSize = (bytes) => {
  if (bytes === 0) return '-'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let i = 0
  while (size >= 1024 && i < units.length - 1) {
    size /= 1024
    i++
  }
  return `${size.toFixed(2)} ${units[i]}`
}

const showLog = (record) => {
  selectedLog.value = record.log_message || '无日志记录'
  logDialog.value = true
}

onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.font-weight-mono { font-family: 'Fira Code', 'Roboto Mono', monospace; }
.border-glow { border: 1px solid rgba(255,255,255,0.08); }
.border-b { border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
.border-t { border-top: 1px solid rgba(255,255,255,0.08) !important; }
.shadow-24 { box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.5) !important; }
.log-container {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.6;
}
</style>
