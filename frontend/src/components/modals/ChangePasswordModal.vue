<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from '../../plugins/element'
import * as api from '../../api'

const props = defineProps({
  modelValue: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:modelValue'])

const isSubmitting = ref(false)
const errorMsg = ref('')
const form = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
})

watch(
  () => props.modelValue,
  (val) => {
    if (val) {
      form.value = { oldPassword: '', newPassword: '', confirmPassword: '' }
      errorMsg.value = ''
    }
  }
)

const close = () => emit('update:modelValue', false)

const submit = async () => {
  errorMsg.value = ''
  const { oldPassword, newPassword, confirmPassword } = form.value
  if (!oldPassword) {
    errorMsg.value = '请输入当前原密码'
    return
  }
  if (newPassword.length < 6) {
    errorMsg.value = '新密码长度至少 6 位'
    return
  }
  if (newPassword !== confirmPassword) {
    errorMsg.value = '两次输入的新密码不一致'
    return
  }
  isSubmitting.value = true
  try {
    await api.changeOwnPassword(oldPassword, newPassword)
    ElMessage.success('密码修改成功！')
    close()
  } catch (err) {
    errorMsg.value = err.message || '修改密码失败'
  } finally {
    isSubmitting.value = false
  }
}
</script>

<template>
  <div v-if="modelValue" class="pwd-modal-overlay" @click.self="close">
    <div class="pwd-modal-box">
      <div class="pwd-modal-head">🔑 修改我的密码</div>
      <div class="pwd-modal-body">
        <div class="pwd-field">
          <label>当前原密码</label>
          <input v-model="form.oldPassword" type="password" placeholder="请输入当前密码" />
        </div>
        <div class="pwd-field">
          <label>新密码（至少 6 位）</label>
          <input v-model="form.newPassword" type="password" placeholder="请输入新密码" />
        </div>
        <div class="pwd-field">
          <label>确认新密码</label>
          <input
            v-model="form.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            @keyup.enter="submit"
          />
        </div>
        <div v-if="errorMsg" class="pwd-err">{{ errorMsg }}</div>
      </div>
      <div class="pwd-modal-foot">
        <button type="button" class="pwd-btn-ghost" @click="close">取消</button>
        <button type="button" class="pwd-btn-primary" :disabled="isSubmitting" @click="submit">
          {{ isSubmitting ? '保存中...' : '确认修改' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pwd-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 210;
  background: rgba(2, 6, 23, 0.66);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.pwd-modal-box {
  width: 400px;
  max-width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.pwd-modal-head {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
}

.pwd-modal-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 13px;
}

.pwd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pwd-field label {
  font-size: 11.5px;
  color: var(--text-secondary);
  font-weight: 600;
}

.pwd-field input {
  height: 38px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.pwd-field input:focus {
  border-color: var(--accent-color);
}

.pwd-err {
  font-size: 12px;
  color: #f87171;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  padding: 8px 10px;
}

.pwd-modal-foot {
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.pwd-btn-ghost {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 12.5px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  cursor: pointer;
}

.pwd-btn-primary {
  padding: 8px 15px;
  border-radius: 8px;
  font-size: 12.5px;
  font-weight: 600;
  color: #ffffff;
  border: none;
  background: var(--accent-gradient);
  cursor: pointer;
}
</style>

