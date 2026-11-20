<script setup>
import { onMounted, ref } from 'vue'
import * as api from '../../api'
import UserDeleteDialog from '../../components/admin/UserDeleteDialog.vue'
import UserFormDialog from '../../components/admin/UserFormDialog.vue'
import UserResetPwdDialog from '../../components/admin/UserResetPwdDialog.vue'
import {
  ElButton,
  ElMessage,
  ElMessageBox,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTag
} from '../../plugins/element'

const props = defineProps({
  currentUser: {
    type: Object,
    default: () => ({ id: '', username: 'admin', role: 'admin' })
  },
  multiUserMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['toggle-multi-user', 'users-changed'])

const users = ref([])
const isLoading = ref(false)

// 弹窗状态
const showNewUserModal = ref(false)
const isSubmittingNew = ref(false)

const showResetPwdModal = ref(false)
const isSubmittingReset = ref(false)
const resetTargetUser = ref(null)

const showDelUserModal = ref(false)
const isSubmittingDel = ref(false)
const deleteTargetUser = ref(null)

const formatTime = (ts) => {
  if (!ts) return '从未登录'
  try {
    const d = new Date(ts * 1000)
    const pad = (n) => String(n).padStart(2, '0')
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
  } catch {
    return '—'
  }
}

const loadUsers = async () => {
  isLoading.value = true
  try {
    const res = await api.listAdminUsers()
    if (res && res.users) {
      users.value = res.users
    }
  } catch (err) {
    ElMessage.error(err.message || '加载用户列表失败')
  } finally {
    isLoading.value = false
  }
}

const handleCreateUser = async (formData) => {
  isSubmittingNew.value = true
  try {
    await api.createAdminUser(formData)
    ElMessage.success(`用户「${formData.username}」创建成功`)
    showNewUserModal.value = false
    await loadUsers()
    emit('users-changed')
  } catch (err) {
    ElMessage.error(err.message || '创建用户失败')
  } finally {
    isSubmittingNew.value = false
  }
}

const handleToggleActive = async (u) => {
  if (u.username === 'admin') {
    ElMessage.warning('系统内置 admin 账号不可禁用')
    return
  }
  const nextActive = !u.is_active
  try {
    await api.updateAdminUser(u.id, { is_active: nextActive })
    u.is_active = nextActive
    ElMessage.success(`已${nextActive ? '启用' : '禁用'}用户「${u.username}」`)
  } catch (err) {
    ElMessage.error(err.message || '修改状态失败')
  }
}

const handleToggleRole = async (u) => {
  if (u.username === 'admin') {
    ElMessage.warning('系统内置 admin 账号角色不可变更')
    return
  }
  const nextRole = u.role === 'admin' ? 'member' : 'admin'
  try {
    await api.updateAdminUser(u.id, { role: nextRole })
    u.role = nextRole
    ElMessage.success(`用户「${u.username}」角色已调整为 ${nextRole}`)
  } catch (err) {
    ElMessage.error(err.message || '调整角色失败')
  }
}

const openResetPwd = (u) => {
  resetTargetUser.value = u
  showResetPwdModal.value = true
}

const handleResetPwd = async (newPassword) => {
  if (!resetTargetUser.value) return
  isSubmittingReset.value = true
  try {
    await api.resetAdminUserPassword(resetTargetUser.value.id, newPassword)
    ElMessage.success(`用户「${resetTargetUser.value.username}」密码重置成功`)
    showResetPwdModal.value = false
  } catch (err) {
    ElMessage.error(err.message || '重置密码失败')
  } finally {
    isSubmittingReset.value = false
  }
}

const openDeleteUser = (u) => {
  if (u.username === 'admin') {
    ElMessage.warning('系统内置 admin 账号不可删除')
    return
  }
  deleteTargetUser.value = u
  showDelUserModal.value = true
}

const handleDeleteUser = async (strategy) => {
  if (!deleteTargetUser.value) return
  isSubmittingDel.value = true
  try {
    await api.deleteAdminUser(deleteTargetUser.value.id, strategy)
    ElMessage.success(`用户「${deleteTargetUser.value.username}」已安全删除`)
    showDelUserModal.value = false
    await loadUsers()
    emit('users-changed')
  } catch (err) {
    ElMessage.error(err.message || '删除用户失败')
  } finally {
    isSubmittingDel.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<template>
  <section class="admin-page user-admin-view">
    <!-- 头部工具栏 -->
    <div class="ap-head">
      <span class="aph-icon">👥</span>
      <div>
        <h1>用户与权限管理</h1>
        <p>全表多租户数据隔离 · 账号密码管控 · 数据归属安全转移</p>
      </div>

      <div class="aph-right">
        <!-- 多用户鉴权开关 -->
        <div class="mode-switch-box">
          <span class="msb-label">多用户鉴权模式：</span>
          <el-switch
            :model-value="multiUserMode"
            size="small"
            active-text="开启"
            inactive-text="单人免登"
            @change="emit('toggle-multi-user')"
          />
        </div>

        <el-button
          type="primary"
          size="small"
          class="btn-new-user"
          @click="showNewUserModal = true"
        >
          + 新建用户
        </el-button>
      </div>
    </div>

    <!-- 用户列表 (Element Plus el-table) -->
    <div class="panel user-table-panel">
      <el-table
        v-loading="isLoading"
        :data="users"
        style="width: 100%"
        class="custom-el-table"
      >
        <el-table-column label="用户 / 账号" min-width="180">
          <template #default="{ row }">
            <div class="ut-user-cell">
              <span class="utu-avatar">{{ (row.display_name || row.username || 'U').charAt(0).toUpperCase() }}</span>
              <div class="utu-meta">
                <b>{{ row.display_name || row.username }}</b>
                <small>{{ row.username }}</small>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色" min-width="110">
          <template #default="{ row }">
            <el-tag
              :type="row.role === 'admin' ? 'danger' : 'info'"
              size="small"
              round
            >
              {{ row.role === 'admin' ? '管理员' : '成员' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="账号状态" min-width="100">
          <template #default="{ row }">
            <span class="ut-status-chip" :class="{ off: !row.is_active }">
              <i class="dot"></i>
              <span>{{ row.is_active ? '正常' : '已禁用' }}</span>
            </span>
          </template>
        </el-table-column>

        <el-table-column label="最后登录" min-width="160">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.last_login_at) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="220" align="right">
          <template #default="{ row }">
            <div class="ut-actions">
              <el-button
                v-if="row.username !== 'admin'"
                size="small"
                link
                type="primary"
                @click="handleToggleRole(row)"
              >
                {{ row.role === 'admin' ? '降为成员' : '设为管理员' }}
              </el-button>

              <el-button
                v-if="row.username !== 'admin'"
                size="small"
                link
                :type="row.is_active ? 'warning' : 'success'"
                @click="handleToggleActive(row)"
              >
                {{ row.is_active ? '禁用' : '启用' }}
              </el-button>

              <el-button
                size="small"
                link
                type="info"
                @click="openResetPwd(row)"
              >
                重置密码
              </el-button>

              <el-button
                v-if="row.username !== 'admin'"
                size="small"
                link
                type="danger"
                @click="openDeleteUser(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 安全防护提示 -->
    <div class="user-note">
      ⚠️ 风险提示：删除用户前系统将强制自动备份 SQLite 数据库文件（<code>.bak</code>）；删除时可选择将名下全部作品、章节、角色卡及素材安全转移给管理员，或连带级联物理清除。
    </div>

    <!-- 弹窗组件群 -->
    <UserFormDialog
      v-model:visible="showNewUserModal"
      :loading="isSubmittingNew"
      @submit="handleCreateUser"
    />

    <UserResetPwdDialog
      v-model:visible="showResetPwdModal"
      :loading="isSubmittingReset"
      :target-user="resetTargetUser"
      @submit="handleResetPwd"
    />

    <UserDeleteDialog
      v-model:visible="showDelUserModal"
      :loading="isSubmittingDel"
      :target-user="deleteTargetUser"
      @submit="handleDeleteUser"
    />
  </section>
</template>

<style scoped>
.user-admin-view {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ap-head {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 16px 20px;
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
}

.aph-icon {
  font-size: 28px;
  line-height: 1;
}

.ap-head h1 {
  font-size: 17px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  margin: 0 0 4px 0;
}

.ap-head p {
  font-size: 11.5px;
  color: var(--text-muted, #64748b);
  margin: 0;
}

.aph-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 16px;
}

.mode-switch-box {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--text-secondary, #cbd5e1);
}

.msb-label {
  color: var(--text-muted, #94a3b8);
}

.btn-new-user {
  background: var(--accent-gradient, linear-gradient(135deg, #0ea5e9, #6366f1));
  border: none;
  font-weight: 600;
}

.panel {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 12px;
}

.ut-user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
}

.utu-avatar {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #fff;
  font-weight: 700;
  font-size: 13px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex: none;
}

.utu-meta {
  display: flex;
  flex-direction: column;
}

.utu-meta b {
  font-size: 13px;
  color: var(--text-primary, #f8fafc);
}

.utu-meta small {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  font-family: var(--font-mono, monospace);
}

.ut-status-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  color: var(--success-color, #10b981);
}

.ut-status-chip .dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: currentColor;
}

.ut-status-chip.off {
  color: var(--text-muted, #64748b);
}

.time-text {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
  font-family: var(--font-mono, monospace);
}

.ut-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
}

.user-note {
  font-size: 11px;
  color: var(--warning-color, #f59e0b);
  line-height: 1.6;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  padding: 10px 14px;
}
</style>

