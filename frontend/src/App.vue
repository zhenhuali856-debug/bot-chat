<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import GlobalTopbar from './components/GlobalTopbar.vue'
import LoginView from './components/LoginView.vue'
import ChangePasswordModal from './components/ChangePasswordModal.vue'
import { useTheme } from './composables/useTheme'
import { useAuthStore } from './stores/auth'

const route = useRoute()
const router = useRouter()
const { initTheme } = useTheme()
const {
  currentUser,
  multiUserMode,
  hasAuthToken,
  isLoginVisible,
  onLoginSuccess,
  logout,
  toggleMultiUserMode
} = useAuthStore()

const isChangePwdVisible = ref(false)

const activeMainTab = computed({
  get: () => (route.meta?.tab === 'admin' ? 'admin' : 'create'),
  set: (tab) => {
    const target = tab === 'admin' ? '/admin/dashboard' : '/workspace'
    if (route.path !== target) {
      router.push(target)
    }
  }
})

onMounted(() => {
  initTheme()
})
</script>

<template>
  <div class="app-shell">
    <!-- 全局一级顶栏：✍️ 创作工作台 / 📊 后台管理 路由 Tab 切换 + 身份菜单 -->
    <GlobalTopbar
      v-model:active-tab="activeMainTab"
      :current-user="currentUser"
      :multi-user-mode="multiUserMode"
      :has-token="hasAuthToken"
      @open-login="isLoginVisible = true"
      @open-change-password="isChangePwdVisible = true"
      @toggle-multi-user="toggleMultiUserMode"
      @logout="logout"
    />

    <!-- 路由视图舞台（创作工作台保留状态缓存，后台管理按路由动态渲染） -->
    <div class="view-stage">
      <router-view v-slot="{ Component }">
        <keep-alive include="WorkspaceView">
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </div>

    <!-- 登录覆盖层（单人模式默认跳过，多用户模式或手动切换账号时显示） -->
    <LoginView
      v-model="isLoginVisible"
      :can-close="!multiUserMode || hasAuthToken"
      :multi-user-mode="multiUserMode"
      @login-success="onLoginSuccess"
    />

    <!-- 修改自己密码弹窗 -->
    <ChangePasswordModal v-model="isChangePwdVisible" />
  </div>
</template>

<style scoped>
.app-shell {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--bg-primary);
}

.view-stage {
  flex: 1;
  min-height: 0;
  width: 100%;
  display: flex;
  overflow: hidden;
  position: relative;
}
</style>
