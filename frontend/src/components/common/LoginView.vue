<script setup>
import { ref, watch } from 'vue'
import * as api from '../../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  },
  canClose: {
    type: Boolean,
    default: false
  },
  multiUserMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue', 'login-success'])

const username = ref('admin')
const password = ref('')
const isSubmitting = ref(false)
const errorMsg = ref('')

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      errorMsg.value = ''
      password.value = ''
    }
  }
)

const handleSubmit = async () => {
  errorMsg.value = ''
  const u = username.value.trim()
  if (!u || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  isSubmitting.value = true
  try {
    const res = await api.login(u, password.value)
    api.setAuthToken(res.token)
    emit('login-success', res)
    emit('update:modelValue', false)
  } catch (err) {
    errorMsg.value = err.message || '登录失败，请检查用户名或密码'
  } finally {
    isSubmitting.value = false
  }
}

const handleClose = () => {
  if (!props.canClose) return
  emit('update:modelValue', false)
}
</script>

<template>
  <div v-if="modelValue" class="login-overlay" @click.self="handleClose">
    <div class="login-card">
      <div class="lc-top">
        <div class="lc-logo">🐇</div>
        <button
          v-if="canClose"
          type="button"
          class="lc-close"
          title="返回工作台"
          @click="handleClose"
        >
          ✕
        </button>
      </div>
      <h2>灵感兔 · 创作工作台</h2>
      <p class="lc-sub">
        {{ multiUserMode ? '当前已开启多用户鉴权模式，请登录后进入你的专属创作空间。' : '输入账号密码切换登录身份（默认管理员账号 admin，初始密码 admin123）。' }}
      </p>

      <form @submit.prevent="handleSubmit">
        <div class="lc-field">
          <label>用户名</label>
          <input
            v-model="username"
            type="text"
            autocomplete="username"
            placeholder="请输入用户名（如 admin / writer01）"
          />
        </div>
        <div class="lc-field">
          <label>密码</label>
          <input
            v-model="password"
            type="password"
            autocomplete="current-password"
            placeholder="请输入密码"
          />
        </div>

        <div v-if="errorMsg" class="lc-err">{{ errorMsg }}</div>

        <button type="submit" class="lc-btn" :disabled="isSubmitting">
          {{ isSubmitting ? '登录中...' : '登 录' }}
        </button>
      </form>

      <div class="lc-mode">
        <b>单人模式默认免登录</b>：本机启动时自动以唯一管理员身份进入，无需看到此页。仅当管理员显式开启「多用户模式」后才需要登录，不降低单人本地使用体验。
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(15, 23, 42, 0.88);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.login-card {
  width: 390px;
  max-width: 94%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 16px;
  padding: 30px 32px;
  box-shadow: 0 24px 70px rgba(0, 0, 0, 0.5);
}

.lc-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}

.lc-logo {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: var(--accent-gradient);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
}

.lc-close {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-primary);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 13px;
}

.lc-close:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.login-card h2 {
  font-size: 20px;
  color: var(--text-primary);
  font-weight: 700;
  margin: 0;
}

.lc-sub {
  font-size: 12px;
  color: var(--text-muted);
  margin: 6px 0 22px;
  line-height: 1.55;
}

.lc-field {
  margin-bottom: 14px;
}

.lc-field label {
  display: block;
  font-size: 11.5px;
  color: var(--text-secondary);
  margin-bottom: 6px;
  font-weight: 600;
}

.lc-field input {
  width: 100%;
  height: 40px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 9px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
  box-sizing: border-box;
}

.lc-field input:focus {
  border-color: var(--accent-color);
}

.lc-err {
  font-size: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
  margin-bottom: 12px;
}

.lc-btn {
  width: 100%;
  height: 42px;
  border-radius: 10px;
  border: none;
  background: var(--accent-gradient);
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  margin-top: 4px;
  cursor: pointer;
  transition: filter 0.15s ease;
}

.lc-btn:hover:not(:disabled) {
  filter: brightness(1.08);
}

.lc-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.lc-mode {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color);
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.6;
}

.lc-mode b {
  color: var(--success-color, #10b981);
}
</style>

