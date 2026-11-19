<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from '../plugins/element'
import { useAuthStore } from '../stores/auth'

const route = useRoute()
const router = useRouter()
const { currentUser, multiUserMode, isAdmin, toggleMultiUserMode } = useAuthStore()

const activeSubPage = computed(() =>
  route.path.startsWith('/admin/users') ? 'user' : 'dash'
)

const switchPage = (page) => {
  if (page === 'user' && !isAdmin.value) {
    ElMessage.warning('权限不足：仅管理员可访问用户管理')
    return
  }
  router.push(page === 'user' ? '/admin/users' : '/admin/dashboard')
}

watch(isAdmin, (val) => {
  if (!val && activeSubPage.value === 'user') {
    router.replace('/admin/dashboard')
  }
})
</script>

<template>
  <div class="admin-view">
    <!-- 后台左侧子导航 -->
    <aside class="admin-side">
      <div class="as-head">
        <div class="ash-kicker">ADMIN CONSOLE</div>
        <div class="ash-title">后台管理</div>
        <div class="ash-desc">用户权限与创作数据看板</div>
      </div>

      <div class="as-nav">
        <div
          class="as-nav-item"
          :class="{ active: activeSubPage === 'dash' }"
          @click="switchPage('dash')"
        >
          <span class="asn-ic">📊</span>
          <span>数据看板</span>
        </div>
        <div
          class="as-nav-item"
          :class="{ active: activeSubPage === 'user', locked: !isAdmin }"
          @click="switchPage('user')"
        >
          <span class="asn-ic">👥</span>
          <span>用户管理</span>
          <span v-if="!isAdmin" class="asn-lock">🔒</span>
        </div>
      </div>

      <div class="as-section">系统状态</div>
      <div class="as-meta">
        <div class="as-meta-card">
          <div class="amc-row">
            <span>服务</span>
            <b style="color: var(--success-color, #10b981)">● 运行中</b>
          </div>
          <div class="amc-row">
            <span>隔离策略</span>
            <b style="color: var(--accent-color)">全表 user_id</b>
          </div>
          <div class="amc-row">
            <span>登录模式</span>
            <b :style="{ color: multiUserMode ? '#f59e0b' : 'var(--success-color, #10b981)' }">
              {{ multiUserMode ? '多用户鉴权' : '单人免登录' }}
            </b>
          </div>
          <div class="amc-row">
            <span>当前视角</span>
            <b>{{ isAdmin ? '全站汇总' : '仅个人数据' }}</b>
          </div>
          <div class="amc-hint">
            {{
              isAdmin
                ? '管理员可见全站汇总数据与用户管理入口。'
                : '成员仅可见自己的作品数据与看板，无用户管理入口。'
            }}
          </div>
        </div>
      </div>
    </aside>

    <!-- 后台右侧内容：子路由出口（DashboardPanel / UserAdminPanel） -->
    <main class="admin-main">
      <router-view v-slot="{ Component }">
        <component
          :is="Component"
          :current-user="currentUser"
          :multi-user-mode="multiUserMode"
          @toggle-multi-user="toggleMultiUserMode"
        />
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.admin-view {
  width: 100%;
  height: 100%;
  display: flex;
  overflow: hidden;
  background: var(--bg-primary);
}

.admin-side {
  width: 232px;
  flex: none;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
}

.as-head {
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--border-color);
}

.as-head .ash-kicker {
  font-size: 10.5px;
  color: var(--accent-color);
  font-weight: 700;
  letter-spacing: 1px;
  text-transform: uppercase;
}

.as-head .ash-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin-top: 5px;
}

.as-head .ash-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 4px;
  line-height: 1.5;
}

.as-nav {
  padding: 12px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.as-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  user-select: none;
}

.as-nav-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.as-nav-item.active {
  color: #ffffff;
  background: var(--accent-gradient);
  box-shadow: 0 2px 10px rgba(59, 130, 246, 0.3);
}

.as-nav-item .asn-ic {
  font-size: 15px;
  width: 18px;
  text-align: center;
}

.as-nav-item .asn-lock {
  margin-left: auto;
  font-size: 10px;
  opacity: 0.75;
}

.as-nav-item.locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.as-nav-item.locked:hover {
  background: transparent;
  color: var(--text-secondary);
}

.as-section {
  padding: 14px 20px 6px;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.as-meta {
  margin-top: auto;
  padding: 14px 16px;
  border-top: 1px solid var(--border-color);
}

.as-meta-card {
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 11px 12px;
}

.as-meta-card .amc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 7px;
  font-size: 11px;
  color: var(--text-secondary);
  margin: 4px 0;
}

.as-meta-card .amc-hint {
  font-size: 10.5px;
  color: var(--text-muted);
  line-height: 1.5;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--border-color);
}

.admin-main {
  flex: 1;
  overflow-y: auto;
  background: var(--bg-primary);
}
</style>

