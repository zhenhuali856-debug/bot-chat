import { createRouter, createWebHashHistory } from 'vue-router'
import { ElMessage } from '../plugins/element'
import { useAuthStore } from '../stores/auth'
import WorkspaceView from '../views/workspace/WorkspaceView.vue'

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
    component: () => import('../views/admin/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    meta: { tab: 'admin', title: '后台管理' },
    children: [
      {
        path: 'dashboard',
        name: 'admin-dashboard',
        component: () => import('../views/admin/DashboardView.vue'),
        meta: { tab: 'admin', title: '创作数据看板' }
      },
      {
        path: 'monitor',
        name: 'admin-monitor',
        component: () => import('../views/admin/MonitorView.vue'),
        meta: { tab: 'admin', title: '运营监控中心' }
      },
      {
        path: 'users',
        name: 'admin-users',
        component: () => import('../views/admin/UserAdminView.vue'),
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

