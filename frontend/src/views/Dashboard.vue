<template>
  <div>
    <!-- Header Stats -->
    <v-row class="mb-6">
      <v-col cols="12" md="4">
        <v-card class="py-4 px-2" color="primary" variant="tonal">
          <div class="d-flex flex-row align-center">
            <v-avatar color="primary" size="x-large" variant="flat" class="mx-4">
              <v-icon icon="mdi-folder-multiple" size="large"></v-icon>
            </v-avatar>
            <div>
              <div class="text-h4 font-weight-bold">{{ projects.length }}</div>
              <div class="text-caption text-uppercase font-weight-bold opacity-70">活跃任务</div>
            </div>
          </div>
        </v-card>
      </v-col>
      <v-col cols="12" md="4">
        <v-card class="py-4 px-2" color="success" variant="tonal">
          <div class="d-flex flex-row align-center">
            <v-avatar color="success" size="x-large" variant="flat" class="mx-4">
              <v-icon icon="mdi-check-circle" size="large"></v-icon>
            </v-avatar>
            <div>
              <div class="text-h4 font-weight-bold">正常</div>
              <div class="text-caption text-uppercase font-weight-bold opacity-70">系统状态</div>
            </div>
          </div>
        </v-card>
      </v-col>
    </v-row>

    <div class="d-flex align-center mb-4 gap-2">
      <div>
        <h2 class="text-h5 font-weight-bold">备份任务列表</h2>
        <div class="text-caption text-grey">管理和监控您的所有数据备份计划</div>
      </div>
      <v-spacer></v-spacer>
      
      <!-- Import/Export Tools -->
      <v-tooltip location="top" text="将所有任务配置导出为单 JSON 文件，用于备份迁移">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" variant="outlined" color="grey-lighten-1" prepend-icon="mdi-download" @click="exportAllProjects">导出配置</v-btn>
        </template>
      </v-tooltip>

      <v-tooltip location="top" text="从 JSON 文件批量导入任务配置，支持版本自动兼容">
        <template v-slot:activator="{ props }">
          <v-btn v-bind="props" variant="outlined" color="grey-lighten-1" prepend-icon="mdi-upload" @click="$refs.fileInput.click()">导入配置</v-btn>
        </template>
      </v-tooltip>
      
      <input type="file" ref="fileInput" hidden accept=".json" @change="handleImport">

      <v-btn color="primary" prepend-icon="mdi-plus" @click="uiStore.openCreateDialog">新建任务</v-btn>
    </div>

    <!-- Modern List View -->
    <v-card class="pa-0 overflow-hidden" border>
      <v-table hover class="bg-surface">
        <thead>
          <tr>
            <th class="text-left py-4 pl-6" width="25%">任务名称</th>
            <th class="text-left" width="30%">源目录 / 目标目录</th>
            <th class="text-left" width="25%">配置详情</th>
            <th class="text-right pr-6" width="20%">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="project in projects" :key="project.id" class="py-2">
            <td class="pl-6 py-4">
              <div class="d-flex align-center">
                <v-avatar 
                  :color="isRunning(project) ? 'primary' : 'secondary'" 
                  variant="tonal" 
                  rounded 
                  class="mr-4"
                >
                  <v-progress-circular 
                    v-if="isRunning(project)" 
                    :indeterminate="getProjectProgress(project) <= 0"
                    :model-value="getProjectProgress(project)"
                    color="primary" 
                    size="24" 
                    width="3"
                  >
                    <span v-if="getProjectProgress(project) > 0" style="font-size: 8px;">{{ getProjectProgress(project) }}</span>
                  </v-progress-circular>
                  <span v-else class="text-h6 font-weight-bold">{{ project.name.charAt(0).toUpperCase() }}</span>
                </v-avatar>
                <div>
                  <div class="font-weight-bold text-body-1">{{ project.name }}</div>
                  
                  <div v-if="isRunning(project)" class="text-caption text-primary font-weight-bold mt-1 fade-enter-active">
                    {{ project.latest_history?.log_message || '正在准备...' }}
                  </div>
                  <v-chip v-else size="x-small" color="success" class="mt-1" variant="flat">就绪</v-chip>
                </div>
              </div>
            </td>
            
            <td class="py-4">
              <div class="d-flex flex-column gap-2" v-if="!isRunning(project)">
                <div class="d-flex align-center text-caption text-grey-lighten-1">
                  <v-icon size="small" class="mr-2" color="primary">mdi-folder-open</v-icon>
                  <span class="text-truncate" style="max-width: 250px;">{{ project.source_path }}</span>
                </div>
                <div class="d-flex align-center text-caption text-grey-lighten-1">
                  <v-icon size="small" class="mr-2" color="secondary">mdi-cloud-upload</v-icon>
                  <span class="text-truncate" style="max-width: 250px;">{{ project.destination_path }}</span>
                </div>
              </div>

              <!-- Progress Bar when running -->
              <div v-else class="pr-6">
                <div class="d-flex justify-space-between text-caption mb-1">
                  <span class="text-grey">{{ isRestore(project) ? '还原中' : '执行中' }}</span>
                  <span class="text-primary font-weight-bold">
                    {{ isRestore(project) ? '正在还原数据...' : (getProjectProgress(project) > 0 ? getProjectProgress(project) + '%' : '处理数据中...') }}
                  </span>
                </div>
                <v-progress-linear
                  :indeterminate="getProjectProgress(project) <= 0"
                  :model-value="getProjectProgress(project)"
                  :color="isRestore(project) ? 'warning' : 'primary'"
                  rounded
                  height="6"
                  class="mb-2"
                  striped
                  active
                ></v-progress-linear>
                <div class="text-caption text-grey-darken-1 text-truncate">
                  {{ isRestore(project) ? '源: ' + project.source_path : '目标: ' + project.destination_path }}
                </div>
              </div>
            </td>

            <!-- Configuration Details -->
            <td class="py-4">
              <div class="d-flex flex-column gap-1 align-start">
                <!-- Badges -->
                <div class="d-flex flex-wrap gap-2 mb-1">
                  <v-chip size="x-small" variant="outlined" color="secondary" class="font-weight-medium">
                    {{ getFormatLabel(project) }}
                  </v-chip>
                  <v-chip size="x-small" variant="flat" :color="project.destination_type === 'cloud' ? 'primary' : 'info'" class="font-weight-medium">
                    <v-icon start :icon="project.destination_type === 'cloud' ? 'mdi-cloud-outline' : 'mdi-harddisk'" size="x-small"></v-icon>
                    {{ project.destination_type === 'cloud' ? '云端网盘' : '本地磁盘' }}
                  </v-chip>
                  <v-chip v-if="project.encryption_password" size="x-small" variant="outlined" color="warning" class="font-weight-medium">
                    <v-icon start icon="mdi-lock" size="x-small"></v-icon>加密
                  </v-chip>
                </div>

                <!-- Schedule -->
                <div class="d-flex align-center text-caption" :class="project.schedule?.is_active ? 'text-white' : 'text-grey'">
                  <v-icon size="small" icon="mdi-clock-outline" class="mr-2" :color="project.schedule?.is_active ? 'success' : 'grey'"></v-icon>
                  {{ formatSchedule(project) }}
                  <span v-if="project.schedule?.is_active && project.next_run_time" class="ml-2 text-grey-darken-1">
                     (下次: {{ formatNextRun(project.next_run_time) }})
                  </span>
                </div>
              </div>
            </td>

            <td class="text-right pr-6 py-4">
              <div class="d-flex align-center justify-end">
                  <!-- Main Actions -->
                  <v-btn 
                    v-if="isRunning(project) && !isRestore(project)"
                    icon="mdi-stop"
                    variant="text" 
                    color="error" 
                    @click="stopBackup(project.id)"
                    v-tooltip="'停止任务'"
                  ></v-btn>

                  <v-btn 
                    v-if="isRestore(project)"
                    icon
                    variant="text" 
                    color="warning" 
                    disabled
                  >
                    <v-progress-circular indeterminate size="20" width="2"></v-progress-circular>
                    <v-tooltip activator="parent" location="top">正在还原数据...</v-tooltip>
                  </v-btn>

                  <v-btn 
                    v-if="!isRunning(project)"
                    icon="mdi-play"
                    variant="text" 
                    color="success" 
                    @click="triggerBackup(project.id)"
                    v-tooltip="'立即运行'"
                  ></v-btn>
                  
                  <v-btn 
                    icon="mdi-history" 
                    variant="text" 
                    color="info" 
                    @click="openHistory(project)"
                    v-tooltip="'查看历史'"
                  ></v-btn>

                  <v-btn 
                    icon="mdi-restore" 
                    variant="text" 
                    color="error" 
                    @click="openRestore(project)"
                    v-tooltip="'还原数据'"
                    :disabled="isRunning(project)"
                  ></v-btn>
                  
                  <!-- More Menu -->
                  <v-menu location="bottom end">
                    <template v-slot:activator="{ props }">
                      <v-btn
                        icon="mdi-dots-vertical"
                        variant="text"
                        color="grey"
                        v-bind="props"
                      ></v-btn>
                    </template>
                    <v-list density="compact" class="bg-surface border-glow">
                      <v-list-item 
                        @click="uiStore.openEditDialog(project)"
                        :disabled="isRunning(project)"
                        prepend-icon="mdi-pencil"
                        title="编辑配置"
                      ></v-list-item>
                      <v-list-item 
                        @click="duplicateProject(project)"
                        :disabled="isRunning(project)"
                        prepend-icon="mdi-content-copy"
                        title="复制任务"
                      ></v-list-item>
                      <v-list-item 
                        @click="confirmDelete(project)"
                        :disabled="isRunning(project)"
                        prepend-icon="mdi-delete"
                        title="删除任务"
                        class="text-error"
                      ></v-list-item>
                    </v-list>
                  </v-menu>
              </div>
            </td>
          </tr>
          
          <tr v-if="projects.length === 0">
            <td colspan="4" class="text-center py-12 text-grey">
              <v-icon size="64" color="grey-darken-3" class="mb-4">mdi-package-variant</v-icon>
              <div>暂无任务，快去创建一个吧</div>
            </td>
          </tr>
        </tbody>
      </v-table>
    </v-card>
    
    <!-- Run Confirmation Dialog (Remark) -->
    <v-dialog v-model="runConfirmDialog" max-width="400">
      <v-card color="surface" class="border-glow">
        <v-card-title class="text-h6 font-weight-bold pa-4 d-flex align-center">
          <v-icon icon="mdi-play-circle" color="success" class="mr-2"></v-icon>
          启动备份任务
        </v-card-title>
        <v-card-text class="pa-4 pt-0">
          <div class="text-caption text-grey mb-4">您可以为本次备份添加备注（可选）</div>
          <v-text-field
            v-model="backupRemark"
            label="备注信息"
            placeholder="例如：发版前备份 / 修复Bug后"
            variant="outlined"
            density="comfortable"
            hide-details
            @keyup.enter="executeTrigger"
          ></v-text-field>
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="runConfirmDialog = false">取消</v-btn>
          <v-btn variant="flat" color="success" @click="executeTrigger">立即启动</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-snackbar v-model="snackbar" :timeout="3000" :color="snackbarColor" location="top">
      <div class="d-flex align-center">
        <v-icon :icon="snackbarColor === 'success' ? 'mdi-check-circle' : (snackbarColor === 'warning' ? 'mdi-alert' : 'mdi-alert-circle')" class="mr-2"></v-icon>
        {{ snackbarText }}
      </div>
    </v-snackbar>

    <!-- Delete Confirmation Dialog -->
    <v-dialog v-model="deleteDialog" max-width="400">
      <v-card color="surface" class="border-glow">
        <v-card-title class="text-h6 font-weight-bold pa-4">确认删除？</v-card-title>
        <v-card-text class="pa-4 pt-0 text-grey-lighten-1">
          确定要删除任务 "{{ projectToDelete?.name }}" 吗？<br>
          删除后不可恢复，且定时任务将停止。
        </v-card-text>
        <v-card-actions class="pa-4">
          <v-spacer></v-spacer>
          <v-btn variant="text" color="grey" @click="deleteDialog = false">取消</v-btn>
          <v-btn variant="flat" color="error" @click="executeDelete" :loading="deleteLoading">删除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- History Dialog -->
    <ProjectHistoryDialog 
      v-model="historyDialogVisible" 
      :project-id="historyProjectId" 
    />

    <!-- Restore Dialog -->
    <ProjectRestoreDialog 
      v-model="restoreDialogVisible" 
      :project-id="restoreProjectId" 
    />

    <!-- Backup Progress Dialog -->
    <BackupProgressDialog
      v-model="backupDialogVisible"
      :project-id="runningProjectId"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import axios from 'axios'
import { useUIStore } from '../stores/ui'
import ProjectHistoryDialog from '../components/ProjectHistoryDialog.vue'
import ProjectRestoreDialog from '../components/ProjectRestoreDialog.vue'
import BackupProgressDialog from '../components/BackupProgressDialog.vue'

const uiStore = useUIStore()
const projects = ref([])
const prevProjectStates = ref({}) // Store previous status to detect completion
const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')
let pollInterval = null

// History Logic
const historyDialogVisible = ref(false)
const historyProjectId = ref(null)

// Restore Logic
const restoreDialogVisible = ref(false)
const restoreProjectId = ref(null)

// Backup Progress Logic
const backupDialogVisible = ref(false)
const runningProjectId = ref(null)
const fileInput = ref(null)

// Run Remark Logic
const runConfirmDialog = ref(false)
const backupRemark = ref('')
const targetRunId = ref(null)

const triggerBackup = (id) => {
  targetRunId.value = id
  backupRemark.value = ''
  runConfirmDialog.value = true
}

const executeTrigger = async () => {
  if (!targetRunId.value) return
  runConfirmDialog.value = false
  
  try {
    await axios.post(`/api/projects/${targetRunId.value}/run`, { 
      remark: backupRemark.value 
    })
    runningProjectId.value = targetRunId.value
    backupDialogVisible.value = true
    fetchProjects()
  } catch (err) {
    showSnackbar('启动失败', 'error')
  }
}

const exportAllProjects = async () => {
  try {
    const res = await axios.get('/api/projects/export/all')
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `StageBackup_Config_${new Date().toISOString().slice(0,10)}.json`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    showSnackbar('任务配置导出成功')
  } catch (err) {
    showSnackbar('导出失败', 'error')
  }
}

const handleImport = async (event) => {
  const file = event.target.files[0]
  if (!file) return
  
  const reader = new FileReader()
  reader.onload = async (e) => {
    try {
      const data = JSON.parse(e.target.result)
      const res = await axios.post('/api/projects/import/all', data)
      showSnackbar(`成功导入 ${res.data.imported_count} 个任务`, 'success')
      fetchProjects()
    } catch (err) {
      showSnackbar('导入失败：文件格式错误或网络异常', 'error')
    }
  }
  reader.readAsText(file)
  event.target.value = '' // Reset input
}

const openHistory = (project) => {
  historyProjectId.value = project.id
  historyDialogVisible.value = true
}

const openRestore = (project) => {
  restoreProjectId.value = project.id
  restoreDialogVisible.value = true
}

const getProjectProgress = (project) => {
  if (!project.latest_history) return 0
  return project.latest_history.progress || 0
}

const getFormatLabel = (p) => {
  const map = {
    'sync': '同步模式',
    '7z': '7z 压缩',
    'tgz': 'Tar.gz 压缩'
  }
  return map[p.archive_format] || p.archive_format || '普通打包'
}

const formatSchedule = (p) => {
  if (!p.schedule || !p.schedule.is_active) return '仅手动运行'
  const s = p.schedule
  if (s.schedule_type === 'interval') {
    const unitMap = { hours: '小时', days: '天', weeks: '周', minutes: '分钟', seconds: '秒' }
    return `每 ${s.interval_value} ${unitMap[s.interval_unit] || s.interval_unit}`
  }
  if (s.schedule_type === 'cron') {
    return `Cron: ${s.cron_expression}`
  }
  return '未知'
}

const formatNextRun = (timeStr) => {
  if (!timeStr) return '-'
  const d = new Date(timeStr)
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// Delete Logic
const deleteDialog = ref(false)
const projectToDelete = ref(null)
const deleteLoading = ref(false)

const duplicateProject = async (project) => {
  try {
    await axios.post(`/api/projects/${project.id}/duplicate`)
    showSnackbar(`任务 "${project.name}" 已复制`, 'success')
    fetchProjects()
  } catch (err) {
    showSnackbar('复制失败', 'error')
  }
}

const confirmDelete = (project) => {
  projectToDelete.value = project
  deleteDialog.value = true
}

const executeDelete = async () => {
  if (!projectToDelete.value) return
  deleteLoading.value = true
  try {
    await axios.delete(`/api/projects/${projectToDelete.value.id}`)
    showSnackbar('任务已删除')
    deleteDialog.value = false
    fetchProjects() 
  } catch (err) {
    showSnackbar('删除失败', 'error')
  } finally {
    deleteLoading.value = false
  }
}

const fetchProjects = async () => {
  try {
    const res = await axios.get('/api/projects/')
    const newProjects = res.data
    
    // Check for status changes
    newProjects.forEach(p => {
      const prevStatus = prevProjectStates.value[p.id]
      const currStatus = p.latest_history?.status
      const isRestoring = p.latest_history?.log_message?.includes('还原')
      
      // Detect Completion
      if (prevStatus === 'running' && currStatus === 'success') {
        if (isRestoring) {
          showSnackbar(`项目 "${p.name}" 还原成功！`, 'success')
        } else {
          if (!backupDialogVisible.value || runningProjectId.value !== p.id) {
             showSnackbar(`项目 "${p.name}" 备份完成`, 'success')
          }
        }
      }
      
      // Detect Failure
      if (prevStatus === 'running' && currStatus === 'failed') {
        if (!backupDialogVisible.value || runningProjectId.value !== p.id) {
            showSnackbar(`项目 "${p.name}" 执行失败`, 'error')
        }
      }
      
      // Update state
      prevProjectStates.value[p.id] = currStatus
    })
    
    projects.value = newProjects
  } catch (err) {
    console.error(err)
  }
}

const showSnackbar = (text, color = 'success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

const isRunning = (project) => {
  return project.latest_history && project.latest_history.status === 'running'
}

const isRestore = (project) => {
  return isRunning(project) && project.latest_history?.log_message?.includes('还原')
}

const stopBackup = async (id) => {
  try {
    await axios.post(`/api/projects/${id}/stop`)
    showSnackbar('正在尝试停止任务...', 'warning')
  } catch (err) {
    showSnackbar('无法发送停止信号', 'error')
  }
}

onMounted(() => {
  fetchProjects()
  pollInterval = setInterval(fetchProjects, 2000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.gap-1 {
  gap: 4px;
}
.gap-2 {
  gap: 8px;
}
.border-glow { box-shadow: 0 0 20px rgba(0,0,0,0.5); border: 1px solid rgba(255,255,255,0.05); }
</style>
