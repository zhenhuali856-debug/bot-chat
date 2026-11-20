<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  activeTab: {
    type: String,
    default: 'create' // 'create' | 'admin'
  },
  currentUser: {
    type: Object,
    default: () => ({ username: 'admin', display_name: '系统管理员', role: 'admin' })
  },
  multiUserMode: {
    type: Boolean,
    default: false
  },
  hasToken: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'update:activeTab',
  'open-login',
  'open-change-password',
  'toggle-multi-user',
  'logout'
])

const isMenuOpen = ref(false)
const userMenuContainer = ref(null)

const isAdmin = computed(() => props.currentUser?.role === 'admin')
const avatarChar = computed(() => {
  const name = props.currentUser?.display_name || props.currentUser?.username || 'A'
  return name.charAt(0).toUpperCase()
})
const statusSub = computed(() => {
  const roleLabel = isAdmin.value ? '管理员' : '成员'
  if (!props.multiUserMode && !props.hasToken) {
    return `${roleLabel} · 单人免登录`
  }
  return `${roleLabel} · 已登录`
})

const toggleMenu = (e) => {
  e.stopPropagation()
  isMenuOpen.value = !isMenuOpen.value
}

const handleDocumentClick = (e) => {
  if (userMenuContainer.value && !userMenuContainer.value.contains(e.target)) {
    isMenuOpen.value = false
  }
}

const triggerAction = (eventName, payload) => {
  isMenuOpen.value = false
  if (payload !== undefined) emit(eventName, payload)
  else emit(eventName)
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
})
</script>

<template>
  <header class="global-topbar">
    <div class="gt-brand">
      <span class="gt-logo">🐇</span>
      <span>灵感兔</span>
      <span class="gt-sub">创作工作台</span>
    </div>

    <div class="gt-tabs">
      <button
        type="button"
        class="gt-tab"
        :class="{ active: activeTab === 'create' }"
        @click="emit('update:activeTab', 'create')"
      >
        ✍️ 创作工作台
      </button>
      <button
        type="button"
        class="gt-tab"
        :class="{ active: activeTab === 'admin' }"
        @click="emit('update:activeTab', 'admin')"
      >
        📊 后台管理
      </button>
    </div>

    <div class="gt-spacer"></div>

    <div ref="userMenuContainer" class="gt-user" @click="toggleMenu">
      <span class="gt-avatar">{{ avatarChar }}</span>
      <span class="gt-uname">
        <b>{{ currentUser?.display_name || currentUser?.username || 'admin' }}</b>
        <small>{{ statusSub }}</small>
      </span>
      <span class="gt-role-chip" :class="isAdmin ? 'admin' : 'member'">
        {{ isAdmin ? 'ADMIN' : 'MEMBER' }}
      </span>
      <span class="gt-caret">▾</span>

      <div v-if="isMenuOpen" class="user-menu show" @click.stop>
        <div class="um-head">
          <b>{{ currentUser?.display_name || currentUser?.username }}</b>
          <div>@{{ currentUser?.username }} · {{ isAdmin ? '管理员权限' : '普通成员' }}</div>
        </div>

        <template v-if="isAdmin">
          <div class="um-label">安全与模式</div>
          <button
            type="button"
            class="um-item"
            @click="triggerAction('toggle-multi-user', !multiUserMode)"
          >
            <span class="um-ic">🛡️</span>
            <span class="flex-1">多用户鉴权</span>
            <span class="um-pill" :class="{ on: multiUserMode }">
              {{ multiUserMode ? '已开启' : '免登录' }}
            </span>
          </button>
          <div class="um-divider"></div>
        </template>

        <div class="um-label">账号操作</div>
        <button type="button" class="um-item" @click="triggerAction('open-change-password')">
          <span class="um-ic">🔑</span>
          <span>修改我的密码</span>
        </button>
        <button type="button" class="um-item" @click="triggerAction('open-login')">
          <span class="um-ic">🔐</span>
          <span>切换账号 / 登录</span>
        </button>
        <div class="um-divider"></div>
        <button type="button" class="um-item danger" @click="triggerAction('logout')">
          <span class="um-ic">↪</span>
          <span>退出登录</span>
        </button>
      </div>
    </div>
  </header>
</template>

<style scoped>
.global-topbar {
  height: 52px;
  flex: none;
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 0 18px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  position: relative;
  z-index: 60;
}

.gt-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  white-space: nowrap;
}

.gt-brand .gt-logo {
  width: 26px;
  height: 26px;
  border-radius: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-gradient);
  font-size: 14px;
}

.gt-brand .gt-sub {
  font-size: 10.5px;
  font-weight: 500;
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 5px;
  padding: 1px 6px;
  margin-left: 2px;
}

.gt-tabs {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: 14px;
  background: var(--bg-primary);
  padding: 4px;
  border-radius: 10px;
  border: 1px solid var(--border-color);
}

.gt-tab {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--text-secondary);
  padding: 6px 15px;
  border-radius: 7px;
  border: none;
  background: transparent;
  cursor: pointer;
  transition: all 0.18s ease;
  white-space: nowrap;
}

.gt-tab:hover {
  color: var(--text-primary);
}

.gt-tab.active {
  background: var(--accent-gradient);
  color: #ffffff;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3);
}

.gt-spacer {
  flex: 1;
}

.gt-user {
  position: relative;
  display: flex;
  align-items: center;
  gap: 9px;
  cursor: pointer;
  padding: 5px 9px;
  border-radius: 9px;
  transition: background 0.15s ease;
  user-select: none;
}

.gt-user:hover {
  background: var(--bg-tertiary);
}

.gt-avatar {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #ffffff;
  font-size: 13px;
  font-weight: 700;
}

.gt-uname {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.gt-uname b {
  font-size: 12.5px;
  color: var(--text-primary);
}

.gt-uname small {
  font-size: 10.5px;
  color: var(--text-muted);
}

.gt-role-chip {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 99px;
}

.gt-role-chip.admin {
  color: #c4b5fd;
  background: rgba(139, 92, 246, 0.18);
  border: 1px solid rgba(139, 92, 246, 0.35);
}

.gt-role-chip.member {
  color: #7dd3fc;
  background: rgba(14, 165, 233, 0.15);
  border: 1px solid rgba(14, 165, 233, 0.3);
}

.gt-caret {
  color: var(--text-muted);
  font-size: 11px;
}

.user-menu {
  position: absolute;
  right: 0;
  top: 46px;
  width: 232px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.45);
  padding: 6px;
  z-index: 120;
}

.user-menu .um-head {
  padding: 10px 10px 8px;
  border-bottom: 1px solid var(--border-color);
  margin-bottom: 4px;
}

.user-menu .um-head b {
  font-size: 13px;
  color: var(--text-primary);
}

.user-menu .um-head div {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}

.um-label {
  padding: 7px 10px 3px;
  font-size: 10px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.um-item {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 9px 10px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
  cursor: pointer;
  width: 100%;
  text-align: left;
  border: none;
  background: transparent;
  transition: background 0.15s ease, color 0.15s ease;
}

.um-item:hover {
  background: var(--bg-tertiary);
  color: var(--text-primary);
}

.um-item .um-ic {
  width: 16px;
  text-align: center;
}

.um-item.danger {
  color: #f87171;
}

.um-item.danger:hover {
  background: rgba(239, 68, 68, 0.12);
  color: #fca5a5;
}

.um-divider {
  height: 1px;
  background: var(--border-color);
  margin: 4px 0;
}

.um-pill {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 99px;
  background: var(--bg-primary);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
}

.um-pill.on {
  color: #10b981;
  background: rgba(16, 185, 129, 0.14);
  border-color: rgba(16, 185, 129, 0.35);
}
</style>

