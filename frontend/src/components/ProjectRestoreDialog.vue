<template>
  <v-dialog v-model="visible" max-width="1000" persistent transition="dialog-bottom-transition">
    <v-card color="surface" class="border-glow overflow-hidden">
      <!-- Header -->
      <div class="d-flex justify-space-between align-center pa-6 bg-error-darken-4 border-b">
        <div class="d-flex align-center">
          <v-avatar color="white" variant="tonal" class="mr-4" rounded>
            <v-icon icon="mdi-restore" color="white"></v-icon>
          </v-avatar>
          <div>
            <h2 class="text-h5 font-weight-bold text-white">数据还原中心</h2>
            <div class="text-caption text-grey-lighten-2">选择一个历史备份点进行恢复</div>
          </div>
        </div>
        <div class="d-flex align-center gap-2">
            <v-btn 
              color="white" 
              variant="outlined" 
              prepend-icon="mdi-delete-alert"
              @click="confirmClearAll"
              :disabled="loading || history.length === 0"
            >
              清空所有备份
            </v-btn>
            <v-btn icon="mdi-close" variant="text" color="white" @click="visible = false"></v-btn>
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
            <div class="py-10 text-center text-grey">暂无可用备份</div>
          </template>
          
          <template v-slot:loading>
            <div class="py-10 text-center">正在加载备份列表...</div>
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
          
          <template v-slot:item.actions="{ item }">
            <div class="d-flex gap-2 justify-end">
              <v-btn size="small" variant="text" color="grey" @click="showLog(item)" v-tooltip="'查看日志'">
                <v-icon>mdi-text-box-outline</v-icon>
              </v-btn>
              <v-btn size="small" variant="text" color="error" @click="confirmDeleteOne(item)" v-tooltip="'删除备份文件'">
                <v-icon>mdi-delete</v-icon>
              </v-btn>
              <v-btn v-if="item.status === 'success'" size="small" variant="flat" color="error" @click="confirmRestore(item)" prepend-icon="mdi-restore">
                立即还原
              </v-btn>
            </div>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- Log Detail Dialog -->
    <v-dialog v-model="logDialog" max-width="800" scrollable>
      <v-card color="background" class="border-glow">
        <v-card-title class="d-flex justify-space-between align-center pa-4 bg-surface-light border-b">
          <span class="text-subtitle-2 text-grey">备份日志详情</span>
          <v-btn icon="mdi-close" variant="text" size="small" color="grey" @click="logDialog = false"></v-btn>
        </v-card-title>
        <v-card-text class="pa-0 bg-black">
           <div class="pa-6 font-weight-mono text-body-2 log-container">
              <div v-for="(line, i) in detailLogs" :key="i" :class="getLineClass(line)">{{ line }}</div>
           </div>
        </v-card-text>
      </v-card>
    </v-dialog>

    <!-- Restore Confirmation Dialog -->
    <v-dialog v-model="restoreDialog" max-width="500">
      <v-card color="surface" class="border-glow border-error shadow-24">
        <v-card-title class="bg-error text-white font-weight-bold pa-4 d-flex align-center">
          <v-icon icon="mdi-alert-octagon" class="mr-2"></v-icon>确认执行还原？
        </v-card-title>
        <v-card-text class="pa-6">
          <div class="mb-6 text-body-1 text-white">เตรียม还原备份：<code class="d-block pa-2 mt-2 bg-black rounded text-primary">{{ targetRestoreFile?.file_name }}</code></div>
          <v-radio-group v-model="restoreMode" color="error" hide-details>
            <v-card variant="tonal" class="mb-3 pa-1" :color="restoreMode === 'overwrite' ? 'info' : 'surface'" @click="restoreMode = 'overwrite'">
              <v-radio value="overwrite" label="增量覆盖 (推荐)">
                <template v-slot:label>
                  <div>
                    <div class="text-body-2 font-weight-bold text-white">增量覆盖 (推荐)</div>
                    <div class="text-caption text-grey">仅替换同名文件，旧文件将被保留。</div>
                  </div>
                </template>
              </v-radio>
            </v-card>
            <v-card variant="tonal" class="pa-1" :color="restoreMode === 'clean' ? 'error' : 'surface'" @click="restoreMode = 'clean'">
              <v-radio value="clean">
                <template v-slot:label>
                  <div>
                    <div class="text-body-2 font-weight-bold text-error">清空后还原 (高危)</div>
                    <div class="text-caption text-grey">先强制清空源目录，再完整解压。</div>
                  </div>
                </template>
              </v-radio>
            </v-card>
          </v-radio-group>
        </v-card-text>
        <v-card-actions class="pa-6 pt-0">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="restoreDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" @click="executeRestore" :loading="restoring" class="px-6">确认还原</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Unified Restore Progress Dialog -->
    <v-dialog v-model="restoreProgressDialog" persistent max-width="600" transition="dialog-bottom-transition">
      <v-card color="surface" class="border-glow">
        <v-card-title class="pa-4 bg-surface-light border-b d-flex justify-space-between align-center">
          <span class="text-h6 font-weight-bold">
             <v-icon icon="mdi-restore" class="mr-2" color="warning"></v-icon>数据还原执行中
          </span>
          <v-btn icon="mdi-window-minimize" variant="text" size="small" color="grey" @click="closeProgressDialog" v-tooltip="'后台运行'"></v-btn>
        </v-card-title>
        <v-card-text class="pa-6 custom-scrollbar" style="max-height: 70vh; overflow-y: auto;">
           <div v-if="restoreStatus === 'running'" class="text-center">
              <v-progress-circular :model-value="restoreProgress" :indeterminate="restoreProgress <= 0" color="warning" size="100" width="8" class="mb-6">
                <span class="text-h5 font-weight-bold">{{ restoreProgress }}%</span>
              </v-progress-circular>
              <div class="text-h6 font-weight-bold mb-2">正在还原数据...</div>
              <v-progress-linear :model-value="restoreProgress" :indeterminate="restoreProgress <= 0" color="warning" rounded height="8" striped active class="mb-4"></v-progress-linear>
           </div>
           <div v-else-if="restoreStatus === 'success'" class="text-center py-4">
              <v-icon icon="mdi-check-circle" color="success" size="80" class="mb-4 pulse-icon"></v-icon>
              <div class="text-h5 font-weight-bold text-success">还原成功！</div>
              <div class="text-body-1 text-grey mt-2">您的源目录数据已成功恢复。</div>
           </div>
           <div v-else-if="restoreStatus === 'failed'" class="text-center py-4">
              <v-icon icon="mdi-alert-circle" color="error" size="80" class="mb-4"></v-icon>
              <div class="text-h5 font-weight-bold text-error">还原失败</div>
              <div class="text-body-1 text-grey mt-2">恢复过程中遇到错误，请检查日志。</div>
           </div>
           <div class="mt-6">
             <div class="d-flex justify-space-between align-center mb-2">
               <span class="text-caption text-grey font-weight-bold">实时终端输出</span>
               <v-chip size="x-small" :color="restoreStatus === 'running' ? 'warning' : (restoreStatus === 'success' ? 'success' : 'error')" variant="outlined">
                  {{ restoreStatus === 'running' ? 'LIVE' : 'FINISHED' }}
               </v-chip>
             </div>
             <v-card variant="tonal" color="grey" class="pa-0 overflow-hidden rounded-lg border">
               <div ref="restoreLogContainer" class="bg-black pa-4 text-caption font-weight-mono log-window">
                 <div v-for="(line, i) in formattedRestoreLogs" :key="i" :class="getLineClass(line)">{{ line }}</div>
               </div>
             </v-card>
           </div>
        </v-card-text>
        <v-divider></v-divider>
        <v-card-actions class="pa-4 bg-surface-light">
          <v-spacer></v-spacer>
          <v-btn v-if="restoreStatus !== 'running'" variant="flat" :color="restoreStatus === 'success' ? 'success' : 'grey'" @click="closeProgressDialog" class="px-6">关闭</v-btn>
          <v-btn v-else variant="text" color="primary" @click="closeProgressDialog">后台运行</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
    
    <!-- Delete Single Confirmation -->
    <v-dialog v-model="deleteOneDialog" max-width="400">
      <v-card color="surface" class="border-glow border-error">
        <v-card-title class="text-h6 font-weight-bold pa-4 text-white">删除备份文件？</v-card-title>
        <v-card-text class="pa-4 pt-0 text-grey-lighten-1">
           确定要永久删除备份文件 <b>{{ targetDeleteFile?.file_name }}</b> 吗？<br>
           此操作不可撤销。
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="deleteOneDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" @click="executeDeleteOne" :loading="deleting">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- Clear All Confirmation -->
    <v-dialog v-model="clearAllDialog" max-width="400">
      <v-card color="surface" class="border-glow border-error">
        <v-card-title class="text-h6 font-weight-bold pa-4 text-white">清空所有备份？</v-card-title>
        <v-card-text class="pa-4 pt-0 text-grey-lighten-1">
           <v-alert type="error" variant="tonal" class="mb-4">
             危险操作：这将删除该任务下所有的物理备份文件！
           </v-alert>
           确定要永久删除所有文件吗？
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="clearAllDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" @click="executeClearAll" :loading="clearing">全部删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="3000" :color="snackbarColor" location="top">{{ snackbarText }}</v-snackbar>
  </v-dialog>
</template>

<script setup>
import { ref, watch, nextTick, onUnmounted, computed } from 'vue'
import axios from 'axios'

const props = defineProps({ modelValue: Boolean, projectId: Number })
const emit = defineEmits(['update:modelValue'])

const visible = ref(props.modelValue)
const history = ref([])
const loading = ref(false)
const logDialog = ref(false)
const selectedLog = ref('')

const detailLogs = computed(() => selectedLog.value.split('\n'))
const getLineClass = (line) => {
  if (line.includes('[INFO]')) return 'log-info'
  if (line.includes('[ADD]') || line.includes('[SYNC]') || line.includes('[PACK]') || line.includes('[UNPACK]')) return 'log-add'
  if (line.includes('[SKIP]')) return 'log-skip'
  if (line.includes('[WARN]')) return 'log-warn'
  if (line.includes('[ERROR]') || line.includes('!!!')) return 'log-error'
  if (line.startsWith('🚀') || line.startsWith('♻️') || line.startsWith('==')) return 'log-header'
  return 'log-default'
}

// Progress State
const restoreProgressDialog = ref(false)
const restoreStatus = ref('running')
const restoreProgress = ref(0)
const restoreLog = ref('')
const restoreLogContainer = ref(null)
let progressPollInterval = null

const formattedRestoreLogs = computed(() => restoreLog.value.split('\n'))

// Confirmations
const restoreDialog = ref(false)
const targetRestoreFile = ref(null)
const restoreMode = ref('overwrite')
const restoring = ref(false)
const deleteOneDialog = ref(false)
const targetDeleteFile = ref(null)
const deleting = ref(false)
const clearAllDialog = ref(false)
const clearing = ref(false)
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')

const headers = [
  { title: '备份状态', key: 'status', width: '100px' },
  { title: '备份时间', key: 'start_time' },
  { title: '文件大小', key: 'file_size_bytes' },
  { title: '操作选项', key: 'actions', sortable: false, align: 'end' },
]

watch(() => props.modelValue, (val) => { visible.value = val; if (val && props.projectId) fetchHistory() })
watch(visible, (val) => emit('update:modelValue', val))

const fetchHistory = async () => {
  loading.value = true
  try { const res = await axios.get(`/api/projects/${props.projectId}/backups`); history.value = res.data }
  catch (err) { console.error(err) } finally { loading.value = false }
}

const confirmRestore = (item) => { targetRestoreFile.value = item; restoreMode.value = 'overwrite'; restoreDialog.value = true }

const executeRestore = async () => {
  if (!targetRestoreFile.value) return
  restoring.value = true
  try {
    await axios.post(`/api/projects/${props.projectId}/restore`, { file_name: targetRestoreFile.value.file_name, restore_mode: restoreMode.value })
    restoreDialog.value = false; restoreStatus.value = 'running'; restoreProgress.value = 0; restoreLog.value = '正在初始化...'; restoreProgressDialog.value = true
    startProgressPolling()
  } catch (err) { 
    snackbarText.value = "请求失败: " + (err.response?.data?.detail || err.message); snackbarColor.value = "error"; snackbar.value = true
  } finally { restoring.value = false }
}

const startProgressPolling = () => {
  if (progressPollInterval) clearInterval(progressPollInterval)
  progressPollInterval = setInterval(async () => {
    try {
      const res = await axios.get(`/api/projects/`)
      const project = res.data.find(p => p.id === props.projectId)
      if (project && project.latest_history) {
        const h = project.latest_history
        if (h.log_message && h.log_message.includes('还原任务启动')) {
           restoreStatus.value = h.status; restoreProgress.value = h.progress || 0; restoreLog.value = h.log_message
           nextTick(() => { if (restoreLogContainer.value) restoreLogContainer.value.scrollTop = restoreLogContainer.value.scrollHeight })
           if (h.status !== 'running') clearInterval(progressPollInterval)
        }
      }
    } catch (err) { console.error("Poll error", err) }
  }, 1000)
}

const closeProgressDialog = () => { restoreProgressDialog.value = false; if (progressPollInterval) clearInterval(progressPollInterval); if (restoreStatus.value === 'success') visible.value = false }

// Common Helpers
const getStatusColor = (status) => { if (status === 'success') return 'success'; if (status === 'failed') return 'error'; return 'info' }
const getStatusText = (status) => { const map = { 'success': '可用', 'failed': '失败', 'running': '处理中' }; return map[status] || status }
const formatDate = (dateStr) => { if (!dateStr) return '-'; return new Date(dateStr).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }
const formatSize = (bytes) => { if (!bytes) return '0 B'; const k = 1024, sizes = ['B', 'KB', 'MB', 'GB', 'TB'], i = Math.floor(Math.log(bytes) / Math.log(k)); return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i] }
const showLog = (item) => { selectedLog.value = item.log_message || '暂无日志'; logDialog.value = true }
const executeDeleteOne = async () => {
  if (!targetDeleteFile.value) return; deleting.value = true
  try {
    await axios.delete(`/api/projects/${props.projectId}/history`, { params: { clean_files: true, file_name: targetDeleteFile.value.file_name } })
    deleteOneDialog.value = false; fetchHistory(); snackbarText.value = "已删除"; snackbarColor.value = "success"; snackbar.value = true
  } finally { deleting.value = false }
}
const confirmDeleteOne = (item) => { targetDeleteFile.value = item; deleteOneDialog.value = true }
const confirmClearAll = () => { clearAllDialog.value = true }
const executeClearAll = async () => {
  clearing.value = true
  try { await axios.delete(`/api/projects/${props.projectId}/history`, { params: { clean_files: true } }); clearAllDialog.value = false; fetchHistory(); snackbarText.value = "已清空"; snackbarColor.value = "success"; snackbar.value = true }
  finally { clearing.value = false }
}
onUnmounted(() => { if (progressPollInterval) clearInterval(progressPollInterval) })
</script>

<style scoped>
.font-weight-mono { font-family: 'Fira Code', 'Roboto Mono', monospace; }
.border-glow { border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 0 40px rgba(0,0,0,0.5); }
.border-b { border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
.bg-error-darken-4 { background-color: #450a0a !important; }
.bg-surface-light { background-color: #1e293b !important; }
.log-window { min-height: 200px; height: auto; overflow: visible; white-space: pre-wrap; line-height: 1.4; }
.log-container { white-space: pre-wrap; word-break: break-all; line-height: 1.5; }

/* Custom Scrollbar for Outer Container */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.2);
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 10px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.2);
}

/* Log Colors */
.log-default { color: #94a3b8; }
.log-info { color: #38bdf8; }
.log-add { color: #4ade80; }
.log-skip { color: #fbbf24; }
.log-warn { color: #fb923c; }
.log-error { color: #f87171; }
.log-header { color: #c084fc; font-weight: bold; }

.custom-table :deep(th) { background-color: #0f172a !important; color: #fca5a5 !important; font-weight: bold !important; text-transform: uppercase; }
.shadow-24 { box-shadow: 0 24px 48px -12px rgba(0, 0, 0, 0.5) !important; }
.pulse-icon { animation: pulse 2s infinite; }
@keyframes pulse { 0% { transform: scale(1); opacity: 1; } 50% { transform: scale(1.1); opacity: 0.8; } 100% { transform: scale(1); opacity: 1; } }
</style>