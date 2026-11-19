import { ref, computed } from 'vue'
import { ElMessage, ElNotification } from '../plugins/element'
import * as api from '../api'

// 全局单例鉴权状态（跨路由与组件共享）
const currentUser = ref({
  id: '',
  username: 'admin',
  display_name: '系统管理员',
  role: 'admin'
})
const multiUserMode = ref(false)
const hasAuthToken = ref(Boolean(api.getAuthToken()))
const isLoginVisible = ref(false)
const authInitialized = ref(false)
const authVersion = ref(0) // 每次登录/登出/切换账号递增，通知各视图刷新数据

let initializedHook = false

export function useAuthStore() {
  if (!initializedHook) {
    initializedHook = true
    api.setOnUnauthorized(() => {
      hasAuthToken.value = false
      isLoginVisible.value = true
    })
  }

  const isAdmin = computed(() => currentUser.value?.role === 'admin')

  const initAuth = async () => {
    try {
      const meRes = await api.getAuthMe()
      if (meRes?.user) {
        currentUser.value = meRes.user
      }
      multiUserMode.value = Boolean(meRes?.multi_user_mode)
      hasAuthToken.value = Boolean(api.getAuthToken())
      isLoginVisible.value = false
      authInitialized.value = true
      authVersion.value += 1
      return true
    } catch {
      hasAuthToken.value = false
      isLoginVisible.value = true
      authInitialized.value = true
      return false
    }
  }

  const onLoginSuccess = (res) => {
    if (res?.user) currentUser.value = res.user
    multiUserMode.value = Boolean(res?.multi_user_mode)
    hasAuthToken.value = true
    isLoginVisible.value = false
    authVersion.value += 1
    ElMessage.success(
      `欢迎回来，${currentUser.value.display_name || currentUser.value.username}`
    )
  }

  const logout = async () => {
    try {
      await api.logout()
    } catch {
      // ignore logout error
    }
    api.clearAuthToken()
    hasAuthToken.value = false
    if (multiUserMode.value) {
      isLoginVisible.value = true
      authVersion.value += 1
      ElMessage.info('已退出登录，请重新登录')
    } else {
      ElMessage.info('已清除本地登录凭证，单人模式下自动切回默认管理员')
      await initAuth()
    }
  }

  const toggleMultiUserMode = async (enabled) => {
    try {
      const res = await api.setAuthMode(enabled)
      multiUserMode.value = Boolean(res.multi_user_mode)
      ElMessage.success(
        res.message || (enabled ? '已开启多用户鉴权模式' : '已切回单人免登录模式')
      )
      if (enabled && !hasAuthToken.value) {
        ElNotification({
          title: '已开启多用户鉴权',
          message:
            '下次刷新或接口校验将要求登录。请使用您的管理员账号登录（默认 admin / admin123）。',
          type: 'warning',
          duration: 5000
        })
        isLoginVisible.value = true
      }
    } catch (err) {
      ElMessage.error(err.message || '切换登录模式失败')
    }
  }

  return {
    currentUser,
    multiUserMode,
    hasAuthToken,
    isLoginVisible,
    authInitialized,
    authVersion,
    isAdmin,
    initAuth,
    onLoginSuccess,
    logout,
    toggleMultiUserMode
  }
}

