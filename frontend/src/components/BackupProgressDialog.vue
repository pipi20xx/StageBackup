<template>
  <v-dialog v-model="visible" persistent max-width="600" transition="dialog-bottom-transition">
    <v-card color="surface" class="border-glow">
      <v-card-title class="pa-4 bg-surface-light border-b d-flex justify-space-between align-center">
        <span class="text-h6 font-weight-bold">
           <v-icon icon="mdi-cloud-upload" class="mr-2" color="primary"></v-icon>
           备份任务执行中
        </span>
        <v-btn icon="mdi-window-minimize" variant="text" size="small" color="grey" @click="closeDialog" v-tooltip="'后台运行'"></v-btn>
      </v-card-title>

                  <v-card-text class="pa-6 custom-scrollbar" style="max-height: 70vh; overflow-y: auto;">
                     <!-- Progress Section -->
                     <div v-if="status === 'running'" class="text-center">
                        <v-progress-circular
                          :model-value="progress"
                          :indeterminate="progress <= 0"
                          color="primary"
                          size="100"
                          width="8"
                          class="mb-6"
                        >
                          <span class="text-h5 font-weight-bold">{{ progress }}%</span>
                        </v-progress-circular>
                        
                        <div class="text-h6 font-weight-bold mb-2">正在处理数据...</div>
                        <v-progress-linear
                          :model-value="progress"
                          :indeterminate="progress <= 0"
                          color="primary"
                          rounded
                          height="8"
                          striped
                          active
                          class="mb-4"
                        ></v-progress-linear>
                     </div>
            
                     <!-- Result States -->
                     <div v-else-if="status === 'success'" class="text-center py-4">
                        <v-icon icon="mdi-check-circle" color="success" size="80" class="mb-4 pulse-icon"></v-icon>
                        <div class="text-h5 font-weight-bold text-success">备份成功！</div>
                        <div class="text-body-1 text-grey mt-2">您的数据已安全存储。</div>
                     </div>
            
                     <div v-else-if="status === 'failed'" class="text-center py-4">
                        <v-icon icon="mdi-alert-circle" color="error" size="80" class="mb-4"></v-icon>
                        <div class="text-h5 font-weight-bold text-error">备份失败</div>
                        <div class="text-body-1 text-grey mt-2">请查看下方日志了解详情。</div>
                     </div>
            
                     <!-- Unified Realtime Log Window -->
                     <div class="mt-6">
                       <div class="d-flex justify-space-between align-center mb-2">
                         <span class="text-caption text-grey font-weight-bold">实时终端输出</span>
                         <v-chip size="x-small" :color="status === 'running' ? 'primary' : (status === 'success' ? 'success' : 'error')" variant="outlined">
                            {{ status === 'running' ? 'LIVE' : 'FINISHED' }}
                         </v-chip>
                       </div>
                       <v-card variant="tonal" color="grey" class="pa-0 overflow-hidden rounded-lg border">
                         <div ref="logContainer" class="bg-black pa-4 text-caption font-weight-mono log-window">
                           <div v-for="(line, i) in formattedLogs" :key="i" :class="getLineClass(line)">
                             {{ line }}
                           </div>
                           <div v-if="!logContent" class="text-grey-darken-2">等待日志流...</div>
                         </div>
                       </v-card>
                     </div>
                  </v-card-text>      
            <v-divider></v-divider>
      
            <v-card-actions class="pa-4 bg-surface-light">
              <v-btn 
                v-if="status === 'running'" 
                variant="text" 
                color="error" 
                prepend-icon="mdi-stop"
                @click="confirmStop"
                :loading="stopping"
              >
                停止任务
              </v-btn>
              
              <v-spacer></v-spacer>
              
              <v-btn 
                v-if="status !== 'running'" 
                variant="flat" 
                :color="status === 'success' ? 'success' : 'grey'" 
                @click="closeDialog"
                class="px-6"
              >
                关闭
              </v-btn>
              <v-btn v-else variant="text" color="primary" @click="closeDialog">后台运行</v-btn>
            </v-card-actions>
          </v-card>
        </v-dialog>
      </template>
      
      <script setup>
      import { ref, watch, nextTick, onUnmounted, computed } from 'vue'
      import axios from 'axios'
      
      const props = defineProps({
        modelValue: Boolean,
        projectId: Number
      })
      
      const emit = defineEmits(['update:modelValue', 'finished'])
      
      const visible = ref(props.modelValue)
      const status = ref('running')
      const progress = ref(0)
      const logContent = ref('')
      const stopping = ref(false)
      const logContainer = ref(null)
      let pollInterval = null
      
      const formattedLogs = computed(() => logContent.value.split('\n'))
      
      const getLineClass = (line) => {
        if (line.includes('[INFO]')) return 'log-info'
        if (line.includes('[ADD]') || line.includes('[SYNC]') || line.includes('[PACK]')) return 'log-add'
        if (line.includes('[SKIP]')) return 'log-skip'
        if (line.includes('[WARN]')) return 'log-warn'
        if (line.includes('[ERROR]') || line.includes('!!!')) return 'log-error'
        if (line.startsWith('🚀') || line.startsWith('==')) return 'log-header'
        return 'log-default'
      }
      
      watch(() => props.modelValue, (val) => {
        visible.value = val
        if (val && props.projectId) {
          status.value = 'running'
          progress.value = 0
          logContent.value = ''
          startPolling()
        } else {
          stopPolling()
        }
      })
      
      watch(visible, (val) => { emit('update:modelValue', val) })
      
      const startPolling = () => {
        stopPolling()
        pollInterval = setInterval(fetchStatus, 1000)
      }
      
      const stopPolling = () => { if (pollInterval) clearInterval(pollInterval) }
      
      const fetchStatus = async () => {
        try {
          const res = await axios.get('/api/projects/')
          const project = res.data.find(p => p.id === props.projectId)
          if (project && project.latest_history) {
            const h = project.latest_history
            if (h.log_message && h.log_message.includes('备份任务启动')) {
               status.value = h.status
               progress.value = h.progress || 0
               logContent.value = h.log_message
               nextTick(() => {
                 if (logContainer.value) logContainer.value.scrollTop = logContainer.value.scrollHeight
               })
               if (h.status !== 'running') {
                 stopPolling()
                 emit('finished')
               }
            }
          }
        } catch (err) { console.error("Poll failed", err) }
      }
      
      const confirmStop = async () => {
        if (!confirm("确定要强制停止当前任务吗？")) return
        stopping.value = true
        try { await axios.post(`/api/projects/${props.projectId}/stop`) }
        catch (e) { console.error(e) } finally { stopping.value = false }
      }
      
      const closeDialog = () => { visible.value = false; stopPolling(); }
      onUnmounted(() => { stopPolling() })
      </script>
      
      <style scoped>
      .border-glow { border: 1px solid rgba(255,255,255,0.08); box-shadow: 0 0 40px rgba(0,0,0,0.5); }
      .border-b { border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
      .bg-surface-light { background-color: #1e293b !important; }
      .font-weight-mono { font-family: 'Fira Code', monospace; }
      .log-window { min-height: 200px; height: auto; overflow: visible; white-space: pre-wrap; line-height: 1.4; }
      
      /* Custom Scrollbar for Outer Container */
      .custom-scrollbar::-webkit-scrollbar {        width: 6px;
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
      
      .pulse-icon { animation: pulse 2s infinite; }
      @keyframes pulse {
        0% { transform: scale(1); opacity: 1; }
        50% { transform: scale(1.1); opacity: 0.8; }
        100% { transform: scale(1); opacity: 1; }
      }
      </style>