<script setup>
import { computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from '../../plugins/element'
import { useAuthStore } from '../../stores/auth'

const route = useRoute()
const router = useRouter()
const { currentUser, multiUserMode, isAdmin, toggleMultiUserMode } = useAuthStore()

const activeSubPage = computed(() => {
  if (route.path.startsWith('/admin/users')) return 'user'
  if (route.path.startsWith('/admin/monitor')) return 'monitor'
  return 'dash'
})

const switchPage = (page) => {
  if (page === 'user' && !isAdmin.value) {
    ElMessage.warning('权限不足：仅管理员可访问用户管理')
    return
  }
  if (page === 'user') {
    router.push('/admin/users')
  } else if (page === 'monitor') {
    router.push('/admin/monitor')
  } else {
    router.push('/admin/dashboard')
  }
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
          :class="{ active: activeSubPage === 'monitor' }"
          @click="switchPage('monitor')"
        >
          <span class="asn-ic">🩺</span>
          <span>运营监控</span>
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

    <!-- 后台右侧内容：子路由出口（DashboardView / MonitorView / UserAdminView） -->
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
  padding: 18px 14px;
  gap: 16px;
  user-select: none;
  overflow-y: auto;
}

.as-head {
  padding: 4px 6px;
}

.ash-kicker {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--accent-color);
  margin-bottom: 2px;
}

.ash-title {
  font-size: 17px;
  font-weight: 800;
  color: var(--text-primary);
}

.ash-desc {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.as-nav {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.as-nav-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 12px;
  border-radius: 9px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  position: relative;
}

.as-nav-item:hover {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.04);
}

.as-nav-item.active {
  color: var(--accent-color);
  background: rgba(59, 130, 246, 0.12);
  border: 1px solid rgba(59, 130, 246, 0.28);
}

.as-nav-item.locked {
  opacity: 0.5;
  cursor: not-allowed;
}

.asn-ic {
  font-size: 15px;
}

.asn-lock {
  margin-left: auto;
  font-size: 11px;
}

.as-section {
  font-size: 10.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--text-muted);
  padding: 0 6px;
  margin-top: 6px;
}

.as-meta {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.as-meta-card {
  background: var(--bg-tertiary, rgba(255, 255, 255, 0.03));
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.amc-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 11.5px;
}

.amc-row span {
  color: var(--text-muted);
}

.amc-row b {
  color: var(--text-primary);
  font-weight: 600;
}

.amc-hint {
  font-size: 10.5px;
  line-height: 1.5;
  color: var(--text-muted);
  border-top: 1px solid var(--border-color);
  padding-top: 8px;
  margin-top: 2px;
}

.admin-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 24px;
}

@media (max-width: 900px) {
  .admin-view {
    flex-direction: column;
  }
  .admin-side {
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }
  .as-nav {
    flex-direction: row;
  }
  .as-meta {
    display: none;
  }
}
</style>

