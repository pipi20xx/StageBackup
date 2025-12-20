<template>
  <div>
    <h2 class="text-h5 font-weight-bold mb-6">系统设置</h2>
    
    <v-row>
      <!-- Filter Rules -->
      <v-col cols="12" md="6">
        <v-card class="border-glow bg-surface h-100">
          <v-card-title class="d-flex align-center">
            <v-icon icon="mdi-filter-cog-outline" color="primary" class="mr-2"></v-icon>
            全局过滤模板
          </v-card-title>
          <v-card-subtitle>
            管理“新建任务”时的推荐过滤规则。
            <div class="text-caption text-grey mt-1">
              这些规则会出现在任务创建向导的“一键添加”列表中，用于快速排除常见的冗余文件。
            </div>
          </v-card-subtitle>
          <v-card-text class="pt-4">
             <v-alert type="info" variant="tonal" density="compact" class="mb-4 text-caption" style="font-size: 11px !important;">
               <b>规则生效逻辑：</b><br>
               - <code>node_modules</code>：排除源目录下<b>所有层级</b>的该文件夹。<br>
               - <code>*.log</code>：排除<b>所有子目录</b>下的日志文件。<br>
               - <code>cache/data</code>：仅针对根目录下的特定路径生效。<br>
               - <b>扫描原理</b>：系统会进行深度优先递归扫描，匹配到的文件夹会被完整忽略。
             </v-alert>
             
             <div class="d-flex gap-2 align-center mb-4">
               <v-text-field 
                 v-model="newPattern" 
                 density="compact" 
                 variant="outlined" 
                 placeholder="输入规则 (如 *.tmp)" 
                 hide-details 
                 @keyup.enter="addPattern"
               ></v-text-field>
               <v-btn color="primary" @click="addPattern" :disabled="!newPattern">添加</v-btn>
             </div>
             
             <div class="d-flex flex-wrap gap-2">
               <v-chip 
                 v-for="p in patterns" 
                 :key="p" 
                 closable 
                 color="info" 
                 variant="outlined" 
                 @click:close="removePattern(p)"
               >
                 {{ p }}
               </v-chip>
             </div>
          </v-card-text>
        </v-card>
      </v-col>
      
      <!-- HTTP Proxy -->
      <v-col cols="12" md="6">
         <v-card class="border-glow bg-surface h-100">
            <v-card-title class="d-flex align-center">
               <v-icon icon="mdi-web" color="info" class="mr-2"></v-icon>
               网络代理设置
            </v-card-title>
            <v-card-subtitle>
               配置系统访问外部网络时的 HTTP 代理。
               <div class="text-caption text-grey mt-1">
                 当服务器处于内网环境时，可用于拉取云端数据或发送 Telegram 机器人通知。
               </div>
            </v-card-subtitle>
            <v-card-text class="pt-4">
               <v-text-field
                 v-model="proxyUrl"
                 label="代理地址"
                 placeholder="http://127.0.0.1:7890"
                 variant="outlined"
                 density="comfortable"
                 prepend-inner-icon="mdi-server-network"
               ></v-text-field>
               
               <v-checkbox
                 v-model="proxyEnabledForTg"
                 label="为 Telegram 通知启用此代理"
                 color="info"
                 hide-details
                 density="compact"
                 class="mt-1"
               ></v-checkbox>
            </v-card-text>
         </v-card>
      </v-col>
      
      <!-- Telegram Notification -->
      <v-col cols="12">
         <v-card class="border-glow bg-surface">
            <v-card-title class="d-flex align-center">
               <v-icon icon="mdi-telegram" color="blue" class="mr-2"></v-icon>
               Telegram 消息通知
            </v-card-title>
            <v-card-subtitle class="mb-2">
               实时获取备份任务的成功或失败提醒。
               <div class="text-caption text-grey mt-1">
                 通过 Telegram Bot API 将任务执行结果推送到您的手机端。
               </div>
            </v-card-subtitle>
            <v-card-text class="pt-4">
               <v-row>
                 <v-col cols="12" md="6">
                   <v-text-field
                     v-model="tgToken"
                     label="Bot Token"
                     placeholder="123456:ABC-DEF..."
                     variant="outlined"
                     density="comfortable"
                     prepend-inner-icon="mdi-robot"
                   ></v-text-field>
                 </v-col>
                 <v-col cols="12" md="6">
                   <v-text-field
                     v-model="tgChatId"
                     label="Chat ID"
                     placeholder="-100123456789"
                     variant="outlined"
                     density="comfortable"
                     prepend-inner-icon="mdi-account-group"
                   ></v-text-field>
                 </v-col>
               </v-row>
            </v-card-text>
            <v-card-actions class="px-4 pb-4">
              <v-spacer></v-spacer>
              <v-btn variant="flat" color="blue" @click="testTelegram" :loading="testingTg" prepend-icon="mdi-send">发送测试消息</v-btn>
            </v-card-actions>
         </v-card>
      </v-col>
    </v-row>

    <!-- Global Save Button -->
    <v-btn
      color="primary"
      icon="mdi-content-save"
      size="x-large"
      class="floating-save-btn"
      elevation="8"
      @click="saveAll"
      :loading="saving"
    ></v-btn>

    <v-snackbar v-model="snackbar" :timeout="2000" :color="snackbarColor">
      {{ snackbarText }}
    </v-snackbar>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const patterns = ref([])
const newPattern = ref('')
const proxyUrl = ref('')
const proxyEnabledForTg = ref(false)
const tgToken = ref('')
const tgChatId = ref('')

const snackbar = ref(false)
const snackbarText = ref('')
const snackbarColor = ref('success')
const saving = ref(false)
const testingTg = ref(false)

const fetchSettings = async () => {
  try {
    const res = await axios.get('/api/settings/')
    
    const p = res.data.find(s => s.key === 'recommended_patterns')
    if (p && p.value) patterns.value = JSON.parse(p.value)
    
    const pr = res.data.find(s => s.key === 'http_proxy')
    if (pr) proxyUrl.value = pr.value

    const ptg = res.data.find(s => s.key === 'proxy_enabled_for_telegram')
    if (ptg) proxyEnabledForTg.value = (ptg.value === 'true')
    
    const t = res.data.find(s => s.key === 'telegram_bot_token')
    if (t) tgToken.value = t.value
    
    const c = res.data.find(s => s.key === 'telegram_chat_id')
    if (c) tgChatId.value = c.value
    
  } catch (err) {
    console.error(err)
  }
}

const saveSetting = async (key, value) => {
  await axios.post('/api/settings/', { key, value })
}

const saveAll = async () => {
  saving.value = true
  try {
    // Save Patterns
    await saveSetting('recommended_patterns', JSON.stringify(patterns.value))
    
    // Save Proxy
    await saveSetting('http_proxy', proxyUrl.value)
    await saveSetting('proxy_enabled_for_telegram', String(proxyEnabledForTg.value))
    
    // Save Telegram
    await saveSetting('telegram_bot_token', tgToken.value)
    await saveSetting('telegram_chat_id', tgChatId.value)
    
    showMsg('所有配置已保存')
  } catch (err) {
    console.error(err)
    showMsg('保存失败', 'error')
  } finally {
    saving.value = false
  }
}

const testTelegram = async () => {
  testingTg.value = true
  // First save to ensure backend has latest
  await saveAll()
  
  try {
    await axios.post('/api/settings/test-notification')
    showMsg('测试消息已发送', 'success')
  } catch (err) { 
    showMsg('发送失败，请检查配置或网络', 'error')
  } finally {
    testingTg.value = false
  }
}

const addPattern = () => {
  if (!newPattern.value) return
  if (!patterns.value.includes(newPattern.value)) {
    patterns.value.push(newPattern.value)
  }
  newPattern.value = ''
}

const removePattern = (p) => {
  patterns.value = patterns.value.filter(item => item !== p)
}

const showMsg = (text, color='success') => {
  snackbarText.value = text
  snackbarColor.value = color
  snackbar.value = true
}

onMounted(() => {
  fetchSettings()
})
</script>

<style scoped>
.border-glow { border: 1px solid rgba(255,255,255,0.08); }
.gap-2 { gap: 8px; }
.floating-save-btn {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 100;
}
</style>
