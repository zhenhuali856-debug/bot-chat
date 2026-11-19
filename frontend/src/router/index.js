import { createRouter, createWebHashHistory } from 'vue-router'
import { ElMessage } from '../plugins/element'
import { useAuthStore } from '../stores/auth'
import WorkspaceView from '../views/WorkspaceView.vue'

const routes = [
  {
    path: '/',
    redirect: '/workspace'
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: WorkspaceView,
    meta: { tab: 'create', title: '创作工作台' }
  },
  {
    path: '/admin',
    name: 'admin',
    component: () => import('../views/AdminView.vue'),
    redirect: '/admin/dashboard',
    meta: { tab: 'admin', title: '后台管理' },
    children: [
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('../components/DashboardPanel.vue'),
        meta: { tab: 'admin', title: '创作数据看板' }
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('../components/UserAdminPanel.vue'),
        meta: { tab: 'admin', title: '用户管理', requiresAdmin: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/workspace'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

// 全局路由守卫：确保鉴权状态已初始化，并拦截非管理员访问管理员专属页面
router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.authInitialized.value) {
    await auth.initAuth()
  }

  if (to.meta?.requiresAdmin && !auth.isAdmin.value) {
    ElMessage.warning('权限不足：仅管理员可访问用户管理')
    return '/admin/dashboard'
  }

  if (to.meta?.title) {
    document.title = `${to.meta.title} - 灵感兔 AI 创作工作台`
  }
  return true
})

export default router

