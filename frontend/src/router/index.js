import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import History from '../views/History.vue'
import GlobalHistory from '../views/GlobalHistory.vue'
import Settings from '../views/Settings.vue'
import Explorer from '../views/Explorer.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard
  },
  {
    path: '/history/:id',
    name: 'History',
    component: History
  },
  {
    path: '/history',
    name: 'GlobalHistory',
    component: GlobalHistory
  },
  {
    path: '/explorer',
    name: 'Explorer',
    component: Explorer
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
