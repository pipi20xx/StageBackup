import { defineStore } from 'pinia'

export const useUIStore = defineStore('ui', {
  state: () => ({
    createDialogVisible: false,
    isEditMode: false,
    editingProject: null
  }),
  actions: {
    openCreateDialog() {
      this.isEditMode = false
      this.editingProject = null
      this.createDialogVisible = true
    },
    openEditDialog(project) {
      this.isEditMode = true
      this.editingProject = project
      this.createDialogVisible = true
    },
    closeCreateDialog() {
      this.createDialogVisible = false
      setTimeout(() => {
        this.isEditMode = false
        this.editingProject = null
      }, 300)
    }
  }
})
