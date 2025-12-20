<template>
  <v-dialog v-model="dialog" max-width="600px">
    <template v-slot:activator="{ props }">
      <v-btn v-bind="props" :icon="icon" :variant="variant" :color="color" @click="openDialog">
        <v-icon>mdi-folder-open</v-icon>
      </v-btn>
    </template>

    <v-card>
      <v-card-title class="d-flex align-center">
        <span class="text-h6">选择路径</span>
        <v-spacer></v-spacer>
        <v-btn icon="mdi-close" variant="text" @click="dialog = false"></v-btn>
      </v-card-title>

      <v-divider></v-divider>

      <!-- Breadcrumbs / Current Path -->
      <v-card-text class="pb-0">
        <v-chip class="mb-2" color="primary" label>
          {{ currentPath }}
        </v-chip>
      </v-card-text>

      <v-card-text style="height: 300px; overflow-y: auto;">
        <div v-if="loading" class="d-flex justify-center mt-4">
          <v-progress-circular indeterminate color="primary"></v-progress-circular>
        </div>

        <v-list v-else density="compact">
          <v-list-item
            v-for="item in items"
            :key="item.path"
            @click="navigate(item)"
            :prepend-icon="item.is_dir ? 'mdi-folder' : 'mdi-file'"
          >
            <v-list-item-title>{{ item.name }}</v-list-item-title>
          </v-list-item>
          
          <v-list-item v-if="items.length === 0" title="此目录下没有文件"></v-list-item>
        </v-list>
      </v-card-text>

      <v-divider></v-divider>

      <v-card-actions>
        <v-spacer></v-spacer>
        <v-btn color="grey" variant="text" @click="dialog = false">取消</v-btn>
        <v-btn color="primary" variant="flat" @click="selectCurrent">选择此目录</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import axios from 'axios'

const props = defineProps({
  modelValue: String,
  icon: { type: Boolean, default: true },
  variant: { type: String, default: 'text' },
  color: { type: String, default: 'default' }
})

const emit = defineEmits(['update:modelValue'])

const dialog = ref(false)
const currentPath = ref('/')
const items = ref([])
const loading = ref(false)

const openDialog = () => {
  // If modelValue has a value, try to start there, otherwise root
  currentPath.value = props.modelValue && props.modelValue !== '' ? props.modelValue : '/'
  fetchDir(currentPath.value)
  dialog.value = true
}

const fetchDir = async (path) => {
  loading.value = true
  try {
    // Encode path component to handle slashes correctly if needed, but query param is standard
    const res = await axios.get('/api/system/browse', { params: { path } })
    items.value = res.data
    currentPath.value = path
  } catch (err) {
    console.error(err)
    // If path not found (e.g. user typed garbage), fallback to root
    if (path !== '/') fetchDir('/')
  } finally {
    loading.value = false
  }
}

const navigate = (item) => {
  if (item.is_dir) {
    fetchDir(item.path)
  }
}

const selectCurrent = () => {
  emit('update:modelValue', currentPath.value)
  dialog.value = false
}
</script>
