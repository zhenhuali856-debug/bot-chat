<script setup>
import { reactive, ref, watch } from 'vue'
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElOption,
  ElSelect
} from '../../plugins/element'

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:visible', 'submit'])

const formRef = ref(null)
const form = reactive({
  username: '',
  display_name: '',
  role: 'member',
  password: ''
})

const rules = {
  username: [
    { required: true, message: '请输入登录账号', trigger: 'blur' },
    { min: 3, max: 32, message: '账号长度在 3 到 32 个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入初始密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度至少 6 位', trigger: 'blur' }
  ]
}

watch(
  () => props.visible,
  (val) => {
    if (val) {
      form.username = ''
      form.display_name = ''
      form.role = 'member'
      form.password = ''
      if (formRef.value) formRef.value.clearValidate()
    }
  }
)

const handleClose = () => {
  emit('update:visible', false)
}

const handleConfirm = async () => {
  if (!formRef.value) return
  await formRef.value.validate((valid) => {
    if (valid) {
      emit('submit', { ...form })
    }
  })
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="新建账号"
    width="460px"
    class="custom-admin-dialog"
    destroy-on-close
    @close="handleClose"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-position="top"
      size="default"
    >
      <el-form-item label="登录账号 *" prop="username">
        <el-input
          v-model="form.username"
          placeholder="英文字母、数字或下划线，3~32 位"
          autocomplete="off"
        />
      </el-form-item>

      <el-form-item label="显示名称" prop="display_name">
        <el-input
          v-model="form.display_name"
          placeholder="用户昵称，如「科幻组-张三」"
          autocomplete="off"
        />
      </el-form-item>

      <el-form-item label="初始角色 *" prop="role">
        <el-select v-model="form.role" style="width: 100%">
          <el-option label="普通成员（member）- 仅限个人创作与个人看板" value="member" />
          <el-option label="系统管理员（admin）- 拥有全站看板与账号管理权限" value="admin" />
        </el-select>
      </el-form-item>

      <el-form-item label="初始密码 *" prop="password">
        <el-input
          v-model="form.password"
          type="password"
          show-password
          placeholder="至少 6 位，首次登录建议修改"
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
          确认创建
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

