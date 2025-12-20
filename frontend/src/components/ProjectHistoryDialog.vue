<template>
  <v-dialog v-model="visible" max-width="1000" persistent transition="dialog-bottom-transition">
    <v-card color="surface" class="border-glow overflow-hidden">
      <!-- Header -->
      <div class="d-flex justify-space-between align-center pa-6 bg-surface-light border-b">
        <div class="d-flex align-center">
          <v-avatar color="primary" variant="tonal" class="mr-4" rounded>
            <v-icon icon="mdi-history"></v-icon>
          </v-avatar>
          <div>
            <h2 class="text-h5 font-weight-bold text-white">任务运行记录</h2>
            <div class="text-caption text-grey-lighten-1">查看详细的文件处理状态与日志</div>
          </div>
        </div>
        <div class="d-flex align-center gap-2">
            <v-btn 
              color="error" 
              variant="text" 
              prepend-icon="mdi-delete-sweep"
              @click="confirmClearHistory"
              :disabled="loading || history.length === 0"
            >
              清空记录
            </v-btn>
            <v-btn icon="mdi-close" variant="text" color="grey" @click="visible = false"></v-btn>
        </div>
      </div>

      <!-- Table Content -->
      <v-card-text class="pa-0" style="height: 600px; overflow-y: auto;">
        <v-data-table
          :headers="headers"
          :items="history"
          :loading="loading"
          density="comfortable"
          class="bg-surface custom-table"
          hover
          fixed-header
          height="600"
        >
          <template v-slot:no-data>
            <div class="py-10 text-center text-grey">暂无备份记录</div>
          </template>
          
          <template v-slot:loading>
            <div class="py-10 text-center">正在加载数据...</div>
          </template>

          <template v-slot:item.status="{ item }">
            <v-chip :color="getStatusColor(item.status)" size="small" variant="flat" class="font-weight-bold">
              {{ getStatusText(item.status) }}
            </v-chip>
          </template>
          
          <template v-slot:item.start_time="{ item }">
            <span class="text-body-2 text-white">{{ formatDate(item.start_time) }}</span>
          </template>
          
          <template v-slot:item.file_size_bytes="{ item }">
             <span class="text-body-2 text-grey-lighten-2">{{ formatSize(item.file_size_bytes) }}</span>
          </template>

          <template v-slot:item.remark="{ item }">
             <span class="text-caption text-grey italic">{{ item.remark || '-' }}</span>
          </template>

          <template v-slot:item.duration="{ item }">
            <span class="text-caption font-weight-mono text-primary">{{ calculateDuration(item.start_time, item.end_time) }}</span>
          </template>
          
          <template v-slot:item.actions="{ item }">
            <div class="d-flex gap-2">
              <v-btn size="small" variant="tonal" color="primary" @click="showLog(item)" prepend-icon="mdi-text-box-outline">
                详情日志
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Unified Log Detail Dialog -->
    <v-dialog v-model="logDialog" max-width="900" scrollable>
      <v-card color="background" class="border-glow shadow-24">
        <v-card-title class="d-flex justify-space-between align-center pa-4 bg-black border-b">
          <span class="text-subtitle-1 font-weight-bold text-white">
            <v-icon icon="mdi-console" class="mr-2" color="primary"></v-icon>终端日志详情
          </span>
          <v-btn icon="mdi-close" variant="text" size="small" color="grey" @click="logDialog = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-0 bg-black">
           <div class="pa-6 font-weight-mono text-body-2 log-container">
              <div v-for="(line, i) in formattedLogs" :key="i" :class="getLineClass(line)">
                {{ line }}
              </div>
           </div>
        </v-card-text>
        <v-card-actions class="bg-black pa-4 border-t">
          <v-btn variant="text" color="grey" size="small" prepend-icon="mdi-content-copy" @click="copyLog">复制全文</v-btn>
          <v-spacer></v-spacer>
          <v-btn variant="flat" color="primary" @click="logDialog = false" class="px-6">返回记录</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clear History Confirmation -->
    <v-dialog v-model="clearDialog" max-width="400">
      <v-card color="surface" class="border-glow">
        <v-card-title class="text-h6 font-weight-bold pa-4">清空历史记录？</v-card-title>
        <v-card-text class="pa-4 pt-0 text-grey-lighten-1">
          确定要清空所有运行日志吗？<br>
          <span class="text-warning text-caption">注意：这仅删除日志记录，不会删除实际的备份文件。</span>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="clearDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" @click="executeClearHistory" :loading="clearing">确认清空</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </v-dialog>
</template>

<script setup>
import { ref, watch, computed } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: Boolean,
  projectId: Number
})

const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const history = ref([])
const loading = ref(false)
const logDialog = ref(false)
const selectedLog = ref('')

// Computed logs for coloring
const formattedLogs = computed(() => {
  return selectedLog.value.split('\n')
})

const getLineClass = (line) => {
  if (line.includes('[INFO]')) return 'log-info'
  if (line.includes('[ADD]') || line.includes('[SYNC]') || line.includes('[PACK]')) return 'log-add'
  if (line.includes('[SKIP]')) return 'log-skip'
  if (line.includes('[WARN]')) return 'log-warn'
  if (line.includes('[ERROR]') || line.includes('!!!')) return 'log-error'
  if (line.startsWith('🚀') || line.startsWith('♻️') || line.startsWith('==')) return 'log-header'
  return 'log-default'
}

// Clear History State
const clearDialog = ref(false)
const clearing = ref(false)

const headers = [
  { title: '运行状态', key: 'status', width: '120px' },
  { title: '备份时间', key: 'start_time' },
  { title: '文件大小', key: 'file_size_bytes' },
  { title: '备注', key: 'remark' },
  { title: '执行耗时', key: 'duration' },
  { title: '操作选项', key: 'actions', sortable: false, align: 'end' },
]

watch(() => props.modelValue, (val) => {
  visible.value = val
  if (val && props.projectId) {
    fetchHistory()
  }
})

watch(visible, (val) => {
  emit('update:modelValue', val)
})

const fetchHistory = async () => {
  loading.value = true
  try {
    const res = await axios.get(`/api/projects/${props.projectId}/history`)
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
  const map = { 'success': '任务成功', 'failed': '执行失败', 'running': '正在处理' }
  return map[status] || status
}

const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN', { 
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' 
  })
}

const formatSize = (bytes) => {
  if (!bytes) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

const calculateDuration = (start, end) => {
  if (!start || !end) return '-'
  const diff = new Date(end) - new Date(start)
  const seconds = Math.floor(diff / 1000)
  if (seconds < 60) return `${seconds}秒`
  const minutes = Math.floor(seconds / 60)
  return `${minutes}分 ${seconds % 60}秒`
}

const showLog = (item) => {
  selectedLog.value = item.log_message || '暂无详细日志信息'
  logDialog.value = true
}

const copyLog = () => {
  navigator.clipboard.writeText(selectedLog.value)
  alert("日志已复制到剪贴板")
}

const confirmClearHistory = () => {
  clearDialog.value = true
}

const executeClearHistory = async () => {
  clearing.value = true
  try {
    await axios.delete(`/api/projects/${props.projectId}/history`, {
      params: { clean_files: false }
    })
    clearDialog.value = false
    fetchHistory()
  } catch (err) {
    console.error(err)
  } finally {
    clearing.value = false
  }
}
</script>

<style scoped>
.font-weight-mono { font-family: 'Fira Code', 'Roboto Mono', monospace; }
.border-glow { border: 1px solid rgba(255,255,255,0.08); }
.border-b { border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
.border-t { border-top: 1px solid rgba(255,255,255,0.08) !important; }
.bg-surface-light { background-color: #1e293b !important; }

.log-container {
  white-space: pre-wrap;
  word-break: break-all;
  line-height: 1.5;
}

/* Unified Log Colors */
.log-default { color: #94a3b8; }
.log-info { color: #38bdf8; } /* Cyan */
.log-add { color: #4ade80; }  /* Green */
.log-skip { color: #fbbf24; } /* Yellow */
.log-warn { color: #fb923c; } /* Orange */
.log-error { color: #f87171; } /* Red */
.log-header { color: #c084fc; font-weight: bold; } /* Purple */

.custom-table :deep(th) {
  background-color: #0f172a !important;
  color: #818cf8 !important;
  font-weight: bold !important;
  text-transform: uppercase;
  letter-spacing: 1px;
}
.shadow-24 { box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.5) !important; }
.gap-2 { gap: 8px; }
</style>
