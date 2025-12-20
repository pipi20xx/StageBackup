<script setup>
import { ref, reactive, watch } from 'vue'
import axios from 'axios'
import FileBrowser from './FileBrowser.vue'
import { useUIStore } from '../stores/ui'

const uiStore = useUIStore()
const step = ref(1)
const steps = ['路径选择', '文件过滤', '策略设置', '自动计划']
const loading = ref(false)
const enable_schedule = ref(true)

const unitItems = [
  { text: '分钟', value: 'minutes' },
  { text: '小时', value: 'hours' },
  { text: '天', value: 'days' },
  { text: '周', value: 'weeks' }
]

const form = reactive({
  name: '',
  source_path: '',
  destination_path: '',
  destination_type: 'cloud', // cloud, local
  archive_format: 'tgz', // sync, tgz, 7z
  use_compression: true,
  compression_level: 1,
  sync_threads: 2,
  sync_mode: 'overwrite', // overwrite, incremental
  encryption_password: '',
  keep_versions: 7,
  exclude_patterns: ''
})

const exclude_list = ref([])

const schedule = reactive({
  schedule_type: 'interval',
  interval_value: 24,
  interval_unit: 'hours',
  cron_expression: ''
})

const recommendedPatterns = ref(['node_modules', '.git', '*.log', '.DS_Store', 'dist'])

const addPattern = (p) => {
  if (!exclude_list.value.includes(p)) {
    exclude_list.value.push(p)
  }
}

// Reset or Populate form when dialog opens
watch(() => uiStore.createDialogVisible, async (val) => {
  if (val) {
    // Fetch Global Patterns
    try {
      const res = await axios.get('/api/settings/')
      const s = res.data.find(x => x.key === 'recommended_patterns')
      if (s && s.value) recommendedPatterns.value = JSON.parse(s.value)
    } catch (e) {
      console.error("Fetch settings failed", e)
    }

    step.value = 1
    if (uiStore.isEditMode && uiStore.editingProject) {
      const p = uiStore.editingProject
      Object.assign(form, {
        name: p.name,
        source_path: p.source_path,
        destination_path: p.destination_path,
        destination_type: p.destination_type || 'cloud',
        archive_format: p.archive_format || (p.use_compression ? 'tgz' : 'sync'),
        use_compression: p.use_compression,
        compression_level: p.compression_level || 1,
        sync_threads: p.sync_threads || 2,
        sync_mode: p.sync_mode || 'overwrite',
        encryption_password: p.encryption_password || '',
        keep_versions: p.keep_versions,
        exclude_patterns: p.exclude_patterns || ''
      })
      exclude_list.value = form.exclude_patterns ? form.exclude_patterns.split(',') : []
      
      try {
        const res = await axios.get(`/api/projects/${p.id}/schedule`)
        const s = res.data
        enable_schedule.value = s.is_active
        schedule.schedule_type = s.schedule_type
        schedule.interval_value = s.interval_value
        schedule.interval_unit = s.interval_unit
        schedule.cron_expression = s.cron_expression || ''
      } catch (e) {
        console.error("加载计划任务失败", e)
      }
    } else {
      enable_schedule.value = true
      Object.assign(form, {
        name: '', source_path: '', destination_path: '',
        destination_type: 'cloud', archive_format: 'tgz',
        use_compression: true, compression_level: 1, sync_threads: 2,
        sync_mode: 'overwrite',
        encryption_password: '', keep_versions: 7, exclude_patterns: ''
      })
      exclude_list.value = []
      schedule.schedule_type = 'interval'
      schedule.interval_value = 24
      schedule.interval_unit = 'hours'
      schedule.cron_expression = ''
    }
  }
})

const submit = async () => {
  if (!form.name || !form.source_path || !form.destination_path) {
    alert("请完整填写任务名称和路径信息")
    step.value = 1
    return
  }
  loading.value = true
  try {
    schedule.is_active = enable_schedule.value
    form.exclude_patterns = exclude_list.value.join(',')
    if (uiStore.isEditMode) {
      const pid = uiStore.editingProject.id
      await axios.put(`/api/projects/${pid}`, form)
      await axios.put(`/api/projects/${pid}/schedule`, schedule)
    } else {
      const projectRes = await axios.post('/api/projects/', form)
      await axios.post(`/api/projects/${projectRes.data.id}/schedule/`, schedule)
    }
    uiStore.closeCreateDialog()
    window.location.reload()
  } catch (err) {
    alert("保存失败: " + (err.response?.data?.detail || err.message))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <v-dialog 
    v-model="uiStore.createDialogVisible" 
    max-width="850" 
    persistent
    scrollable
    transition="dialog-bottom-transition"
  >
    <v-card color="surface" class="border-glow d-flex flex-column" style="max-height: 90vh;">
      <!-- Header -->
      <div class="pa-6 border-b flex-none">
        <div class="d-flex justify-space-between align-center mb-4">
          <div class="d-flex align-center">
            <v-avatar color="primary" variant="tonal" class="mr-4" rounded="lg">
              <v-icon :icon="uiStore.isEditMode ? 'mdi-pencil' : 'mdi-plus-thick'"></v-icon>
            </v-avatar>
            <div>
              <h2 class="text-h5 font-weight-bold text-white">{{ uiStore.isEditMode ? '编辑备份计划' : '新建备份计划' }}</h2>
              <div class="text-caption text-grey">配置您的数据自动备份策略</div>
            </div>
          </div>
          <v-btn icon="mdi-close" variant="text" color="grey" @click="uiStore.closeCreateDialog"></v-btn>
        </div>

        <div class="d-flex align-center justify-space-between px-6 py-3 rounded-lg bg-surface-light border">
          <div 
            v-for="(item, index) in steps" 
            :key="index" 
            class="d-flex align-center gap-2 cursor-pointer step-item" 
            :class="{ 'opacity-30': step < index + 1 }"
            @click="step = index + 1"
          >
            <v-avatar :color="step >= index + 1 ? 'primary' : 'grey-darken-2'" size="24" class="text-caption font-weight-bold">
              <v-icon v-if="step > index + 1" icon="mdi-check" size="14"></v-icon>
              <span v-else>{{ index + 1 }}</span>
            </v-avatar>
            <div class="text-caption font-weight-black" :class="step >= index + 1 ? 'text-white' : 'text-grey'">{{ item }}</div>
            <v-icon v-if="index < steps.length - 1" icon="mdi-chevron-right" size="small" color="grey-darken-2" class="mx-1"></v-icon>
          </div>
        </div>
      </div>

      <!-- Content (Scrollable Area) -->
      <v-card-text class="pa-8 bg-surface overflow-y-auto">
        <v-window v-model="step">
          <!-- Step 1: Paths -->
          <v-window-item :value="1">
            <div class="text-subtitle-1 font-weight-bold mb-6 text-white d-flex align-center">
              <v-icon icon="mdi-folder-search-outline" start color="primary"></v-icon>路径与存储类型
            </div>
            
            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">任务名称</label>
            <div class="text-caption text-grey-darken-1 mb-2">为该备份任务起一个唯一的名称，用于标识和生成文件名。</div>
            <v-text-field v-model="form.name" variant="outlined" placeholder="例如：关键数据备份" bg-color="rgba(0,0,0,0.2)" class="mb-6" hide-details="auto" density="comfortable"></v-text-field>
            
            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">源数据目录</label>
            <div class="text-caption text-grey-darken-1 mb-2">您希望备份的原始文件夹（容器内映射路径）。</div>
            <div class="d-flex align-start gap-3 mb-6">
              <v-text-field v-model="form.source_path" placeholder="容器内源路径" variant="outlined" bg-color="rgba(0,0,0,0.2)" hide-details="auto" density="comfortable"></v-text-field>
              <FileBrowser v-model="form.source_path" color="primary" variant="tonal" :icon="false" />
            </div>

            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">备份目的地</label>
            <div class="text-caption text-grey-darken-1 mb-2">备份文件存放的位置（可以是本地路径或已挂载的网盘路径）。</div>
            <div class="d-flex align-start gap-3 mb-6">
              <v-text-field v-model="form.destination_path" placeholder="目标路径" variant="outlined" bg-color="rgba(0,0,0,0.2)" hide-details="auto" density="comfortable"></v-text-field>
              <FileBrowser v-model="form.destination_path" color="primary" variant="tonal" :icon="false" />
            </div>

            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">存储设备类型</label>
            <div class="text-caption text-grey-darken-1 mb-2">根据目的地属性选择，系统将自动优化传输逻辑。</div>
            <v-item-group v-model="form.destination_type" mandatory>
              <v-row dense>
                <v-col cols="6"><v-item v-slot="{ isSelected, toggle }" value="cloud">
                  <v-card @click="toggle" :color="isSelected ? 'primary' : 'surface-light'" :variant="isSelected ? 'tonal' : 'flat'" class="pa-3 cursor-pointer text-center border h-100">
                    <v-icon icon="mdi-cloud-outline" size="small"></v-icon>
                    <div class="text-caption font-weight-bold mt-1">云端/网盘</div>
                    <div style="font-size: 10px;" class="text-grey mt-1">针对 CloudDrive2/Rclone 优化，先本地缓存再上传</div>
                  </v-card>
                </v-item></v-col>
                <v-col cols="6"><v-item v-slot="{ isSelected, toggle }" value="local">
                  <v-card @click="toggle" :color="isSelected ? 'primary' : 'surface-light'" :variant="isSelected ? 'tonal' : 'flat'" class="pa-3 cursor-pointer text-center border h-100">
                    <v-icon icon="mdi-harddisk" size="small"></v-icon>
                    <div class="text-caption font-weight-bold mt-1">本地磁盘/NAS</div>
                    <div style="font-size: 10px;" class="text-grey mt-1">直接在目标路径打包，减少 IO 开销</div>
                  </v-card>
                </v-item></v-col>
              </v-row>
            </v-item-group>
          </v-window-item>

          <!-- Step 2: Filtering -->
          <v-window-item :value="2">
            <div class="text-subtitle-1 font-weight-bold mb-6 text-white d-flex align-center">
              <v-icon icon="mdi-filter-cog-outline" start color="info"></v-icon>文件过滤规则
            </div>
            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">忽略路径或通配符</label>
            
            <v-alert type="info" variant="tonal" density="compact" class="mb-4 text-caption">
              <div class="font-weight-bold mb-1">编写指南：</div>
              <ul class="pl-4">
                <li><b>全局排除文件</b>：使用通配符如 <code>*.log</code>，将自动扫描并排除<b>所有子文件夹</b>下的日志文件。</li>
                <li><b>全局排除文件夹</b>：直接输入文件夹名如 <code>node_modules</code>，将忽略<b>任何路径深度</b>下的该目录。</li>
                <li><b>指定路径排除</b>：输入相对路径如 <code>data/temp</code>，则仅排除根目录下特定位置的内容。</li>
                <li><b>递归特性</b>：一旦文件夹匹配成功，其内部所有文件和子目录都将被跳过，不再向下扫描。</li>
              </ul>
            </v-alert>

            <v-combobox v-model="exclude_list" placeholder="例如: node_modules" variant="outlined" bg-color="rgba(0,0,0,0.2)" multiple chips closable-chips clearable class="mb-6"></v-combobox>
            <div class="pa-4 rounded-lg bg-surface-light border-dashed">
              <div class="text-caption font-weight-bold text-grey-lighten-1 mb-3">一键添加推荐规则</div>
              <div class="d-flex flex-wrap gap-2">
                <v-chip v-for="p in recommendedPatterns" :key="p" size="small" variant="outlined" color="info" @click="addPattern(p)" class="cursor-pointer">
                  <v-icon start size="x-small">mdi-plus</v-icon>{{ p }}
                </v-chip>
              </div>
            </div>
          </v-window-item>

          <!-- Step 3: Strategy -->
          <v-window-item :value="3">
            <div class="text-subtitle-1 font-weight-bold mb-6 text-white d-flex align-center">
              <v-icon icon="mdi-shield-lock-outline" start color="secondary"></v-icon>传输与加密策略
            </div>
            
            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">传输模式</label>
            <div class="text-caption text-grey-darken-1 mb-3">同步适合做镜像，压缩适合做历史版本归档。</div>
            <v-item-group v-model="form.archive_format" mandatory class="mb-6">
              <v-row dense>
                <v-col cols="12" md="4">
                  <v-item v-slot="{ isSelected, toggle }" value="sync">
                    <v-card @click="toggle" :color="isSelected ? 'secondary' : 'surface-light'" :variant="isSelected ? 'tonal' : 'flat'" class="pa-3 cursor-pointer text-center border h-100">
                      <v-icon icon="mdi-sync" size="small"></v-icon>
                      <div class="text-caption font-weight-bold mt-1">同步模式</div>
                      <div style="font-size: 10px;" class="text-grey">维持 1:1 文件副本</div>
                    </v-card>
                  </v-item>
                </v-col>
                <v-col v-for="m in [{v:'tgz', n:'私有高压', i:'mdi-shield-lock', d:'Tar.gz + AES加密'},{v:'7z', n:'标准 7z', i:'mdi-folder-zip', d:'高压缩比，WinRAR兼容'}]" :key="m.v" cols="6" md="4">
                  <v-item v-slot="{ isSelected, toggle }" :value="m.v">
                    <v-card @click="toggle" :color="isSelected ? 'secondary' : 'surface-light'" :variant="isSelected ? 'tonal' : 'flat'" class="pa-3 cursor-pointer text-center border h-100">
                      <v-icon :icon="m.i" size="small"></v-icon>
                      <div class="text-caption font-weight-bold mt-1">{{ m.n }}</div>
                      <div style="font-size: 10px;" class="text-grey">{{ m.d }}</div>
                    </v-card>
                  </v-item>
                </v-col>
              </v-row>
            </v-item-group>

            <v-expand-transition>
              <div v-if="form.archive_format === 'sync'" class="mb-6 pa-4 rounded-lg bg-surface-light border">
                <div class="text-caption font-weight-bold text-white mb-1">同步策略</div>
                <div class="text-caption text-grey mb-3">覆盖模式会清理目标目录，增量模式仅更新差异。</div>
                <v-radio-group v-model="form.sync_mode" inline hide-details density="compact" class="mb-4">
                  <v-radio label="覆盖 (镜像)" value="overwrite" color="secondary" class="mr-4"></v-radio>
                  <v-radio label="增量 (仅更新差异)" value="incremental" color="secondary"></v-radio>
                </v-radio-group>
                <div class="d-flex justify-space-between text-caption mb-2 text-white">
                  <span>多线程复制: {{ form.sync_threads }} 线程</span>
                </div>
                <v-slider v-model="form.sync_threads" min="1" max="10" step="1" color="secondary" hide-details></v-slider>
              </div>
            </v-expand-transition>

            <v-expand-transition>
              <div v-if="['tgz', '7z'].includes(form.archive_format)" class="mb-6 pa-4 rounded-lg bg-surface-light border text-white">
                <div class="d-flex justify-space-between text-caption mb-2">
                  <span>压缩强度: 等级 {{ form.compression_level }}</span>
                </div>
                <v-slider v-model="form.compression_level" min="1" max="9" step="1" color="secondary" hide-details></v-slider>
                <div class="text-caption text-grey-darken-1 mt-1">等级越高体积越小，但会消耗更多 CPU 和时间。</div>
              </div>
            </v-expand-transition>

            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">访问密码 (可选)</label>
            <div class="text-caption text-grey-darken-1 mb-2">为压缩包设置 AES-256 加密。同步模式下不可用。</div>
            <v-text-field v-model="form.encryption_password" type="password" variant="outlined" placeholder="不设密码" bg-color="rgba(0,0,0,0.2)" prepend-inner-icon="mdi-lock" hide-details="auto" class="mb-6" :disabled="form.archive_format === 'sync'"></v-text-field>
            
            <label class="text-caption font-weight-bold text-grey-lighten-2 mb-1 d-block">保留历史版本数</label>
            <div class="text-caption text-grey-darken-1 mb-2">系统会自动清理旧备份，仅保留最近的 N 份文件。</div>
            <v-text-field v-model.number="form.keep_versions" type="number" variant="outlined" bg-color="rgba(0,0,0,0.2)" prepend-inner-icon="mdi-history" suffix="份" hide-details="auto"></v-text-field>
          </v-window-item>

          <!-- Step 4: Schedule -->
          <v-window-item :value="4">
            <div class="text-subtitle-1 font-weight-bold mb-6 text-white d-flex align-center">
              <v-icon icon="mdi-clock-outline" start color="success"></v-icon>自动化运行计划
            </div>
            <v-switch v-model="enable_schedule" color="success" inset label="启用定时自动备份任务" class="mb-4" hide-details></v-switch>
            <v-expand-transition>
              <div v-if="enable_schedule">
                <v-tabs v-model="schedule.schedule_type" color="success" grow class="mb-6 border-b">
                  <v-tab value="interval">简单间隔</v-tab>
                  <v-tab value="cron">专家 Cron</v-tab>
                </v-tabs>
                <div v-if="schedule.schedule_type === 'interval'" class="d-flex align-center gap-4 pa-6 rounded-lg bg-surface-light border">
                  <span>每隔</span>
                  <v-text-field v-model.number="schedule.interval_value" type="number" variant="outlined" density="compact" hide-details bg-color="black" style="max-width: 80px;"></v-text-field>
                  <v-select v-model="schedule.interval_unit" :items="unitItems" item-title="text" item-value="value" variant="outlined" density="compact" hide-details bg-color="black" style="max-width: 100px;"></v-select>
                  <span>执行一次自动备份</span>
                </div>
                <div v-if="schedule.schedule_type === 'cron'" class="pa-6 rounded-lg bg-surface-light border">
                  <div class="text-caption text-grey mb-4">使用标准 Linux Cron 表达式，例如 <code>0 2 * * *</code> 代表每天凌晨 2 点。</div>
                  <v-text-field v-model="schedule.cron_expression" placeholder="0 2 * * *" variant="outlined" bg-color="black" hide-details></v-text-field>
                </div>
              </div>
            </v-expand-transition>
          </v-window-item>
        </v-window>
      </v-card-text>

      <!-- Footer -->
      <v-divider></v-divider>
      <v-card-actions class="pa-6 bg-surface-light flex-none">
        <v-btn v-if="step > 1" variant="outlined" color="grey-lighten-1" @click="step--" class="px-6">上一步</v-btn>
        <v-spacer></v-spacer>
        <v-btn v-if="step < 4" color="primary" variant="flat" @click="step++" class="px-8" size="large">继续</v-btn>
        <v-btn v-if="step === 4" color="success" variant="flat" @click="submit" :loading="loading" class="px-8" size="large">保存配置</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<style scoped>
.gap-2 { gap: 8px; }
.gap-4 { gap: 16px; }
.bg-surface-light { background-color: #1e293b !important; }
.border-b { border-bottom: 1px solid rgba(255,255,255,0.08) !important; }
.border-glow { border: 1px solid rgba(255,255,255,0.1); box-shadow: 0 0 30px rgba(0,0,0,0.5); }
.border-dashed { border: 1px dashed rgba(255,255,255,0.2) !important; }
.border-active-secondary { border-color: #c084fc !important; border-width: 2px !important; }
.cursor-pointer { cursor: pointer; }
.step-item:hover {
  opacity: 0.8 !important;
  transition: opacity 0.2s;
}
.flex-none { flex: none; }
</style>