<script setup>
import { ref, watch } from 'vue'
import {
  ElAlert,
  ElButton,
  ElDialog,
  ElRadio,
  ElRadioGroup
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

const strategy = ref('transfer')

watch(
  () => props.visible,
  (val) => {
    if (val) strategy.value = 'transfer'
  }
)

const handleClose = () => {
  emit('update:visible', false)
}

const handleConfirm = () => {
  emit('submit', strategy.value)
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="二次确认：删除用户账号"
    width="500px"
    class="custom-admin-dialog"
    destroy-on-close
    @close="handleClose"
  >
    <div v-if="targetUser" class="del-confirm-content">
      <el-alert
        type="warning"
        :closable="false"
        show-icon
        style="margin-bottom: 16px"
      >
        <template #title>
          <span>即将永久删除账号：<b>{{ targetUser.username }}</b> ({{ targetUser.display_name || '无昵称' }})</span>
        </template>
      </el-alert>

      <div class="strategy-label">请选择该用户名下作品、章节及素材资产的处理策略：</div>

      <el-radio-group v-model="strategy" class="strategy-group">
        <el-radio label="transfer" class="strategy-radio">
          <div class="sr-content">
            <b>安全转移给系统管理员（推荐）</b>
            <small>名下所有作品、章节、角色卡、素材与历史会话归属变更为 admin，数据不丢失。</small>
          </div>
        </el-radio>
        <el-radio label="delete" class="strategy-radio">
          <div class="sr-content">
            <b style="color: var(--danger-color, #ef4444)">彻底级联清除所有业务数据</b>
            <small>名下全套作品、正文、版本历史与会话将物理抹除，操作不可撤销。</small>
          </div>
        </el-radio>
      </el-radio-group>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleClose">取消</el-button>
        <el-button
          type="danger"
          :loading="loading"
          @click="handleConfirm"
        >
          确认永久删除
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style scoped>
.del-confirm-content {
  font-size: 13px;
  color: var(--text-secondary, #cbd5e1);
}

.strategy-label {
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--text-primary, #f8fafc);
}

.strategy-group {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: flex-start;
}

.strategy-radio {
  display: flex;
  align-items: flex-start;
  height: auto;
  padding: 10px 12px;
  background: var(--bg-primary, #0f172a);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 8px;
  width: 100%;
  margin-right: 0;
}

.sr-content {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-left: 6px;
  text-align: left;
}

.sr-content small {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  line-height: 1.4;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>

