<script setup>
import { ref, watch } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput
} from '../../plugins/element'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  },
  targetUser: {
    type: Object,
    default: () => null
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const newPassword = ref('')
const errorMsg = ref('')

watch(
  () => props.visible,
  (val) => {
    if (val) {
      newPassword.value = ''
      errorMsg.value = ''
    }
  }
)

const handleClose = () => {
  emit('update:visible', false)
}

const handleConfirm = () => {
  if (!newPassword.value || newPassword.value.length < 6) {
    errorMsg.value = '新密码长度至少需要 6 位'
    return
  }
  emit('submit', newPassword.value)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    :title="`重置密码：${targetUser?.username || ''}`"
    width="420px"
    class="custom-admin-dialog"
    destroy-on-close
    @close="handleClose"
  >
    <el-form label-position="top">
      <el-form-item label="设置新密码 *" :error="errorMsg">
        <el-input
          v-model="newPassword"
          type="password"
          show-password
          placeholder="至少 6 位新密码"
          autocomplete="new-password"
        />
      </el-form-item>
    </el-form>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="primary"
          :loading="loading"
          @click="handleConfirm"
        >
          确认重置
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

