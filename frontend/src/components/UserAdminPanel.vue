<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from '../plugins/element'
import * as api from '../api'

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

// 弹窗 1：新建用户
const showNewUserModal = ref(false)
const isSubmittingNew = ref(false)
const newUserForm = ref({
  username: '',
  display_name: '',
  role: 'member',
  password: ''
})
const newUserErrors = ref({
  username: '',
  password: ''
})

// 弹窗 2：重置密码
const showResetPwdModal = ref(false)
const isSubmittingReset = ref(false)
const resetTargetUser = ref(null)
const resetNewPassword = ref('')
const resetPwdError = ref('')

// 弹窗 3：删除用户二次确认
const showDelUserModal = ref(false)
const isSubmittingDel = ref(false)
const deleteTargetUser = ref(null)
const deleteStrategy = ref('transfer')

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
    users.value = res.users || []
  } catch (err) {
    ElMessage.error(err.message || '加载用户列表失败')
  } finally {
    isLoading.value = false
  }
}

const openNewUser = () => {
  newUserForm.value = { username: '', display_name: '', role: 'member', password: '' }
  newUserErrors.value = { username: '', password: '' }
  showNewUserModal.value = true
}

const submitNewUser = async () => {
  const uname = newUserForm.value.username.trim()
  const pwd = newUserForm.value.password
  newUserErrors.value.username = uname ? '' : '请输入用户名'
  newUserErrors.value.password = pwd.length >= 6 ? '' : '密码至少 6 位'
  if (!uname || pwd.length < 6) return

  isSubmittingNew.value = true
  try {
    await api.createAdminUser({
      username: uname,
      display_name: newUserForm.value.display_name.trim() || uname,
      role: newUserForm.value.role,
      password: pwd
    })
    showNewUserModal.value = false
    ElMessage.success(`用户 ${uname} 创建成功（密码已 PBKDF2 加盐存储）`)
    await loadUsers()
    emit('users-changed')
  } catch (err) {
    ElMessage.error(err.message || '创建用户失败')
  } finally {
    isSubmittingNew.value = false
  }
}

const handleChangeRole = async (user) => {
  if (user.username === 'admin') {
    ElMessage.warning('系统默认管理员 admin 不可降级')
    return
  }
  const nextRole = user.role === 'admin' ? 'member' : 'admin'
  try {
    await api.updateAdminUser(user.id, { role: nextRole })
    ElMessage.success(`用户 ${user.username} 角色已改为 ${nextRole === 'admin' ? '管理员' : '成员'}`)
    await loadUsers()
    emit('users-changed')
  } catch (err) {
    ElMessage.error(err.message || '修改角色失败')
  }
}

const handleToggleActive = async (user) => {
  if (user.username === 'admin') {
    ElMessage.warning('系统默认管理员 admin 不可禁用')
    return
  }
  const nextActive = !user.is_active
  try {
    await api.updateAdminUser(user.id, { is_active: nextActive })
    ElMessage.success(`用户 ${user.username} 已${nextActive ? '启用' : '禁用'}`)
    await loadUsers()
  } catch (err) {
    ElMessage.error(err.message || '状态更新失败')
  }
}

const openResetPwd = (user) => {
  resetTargetUser.value = user
  resetNewPassword.value = ''
  resetPwdError.value = ''
  showResetPwdModal.value = true
}

const submitResetPwd = async () => {
  if (!resetTargetUser.value) return
  if (resetNewPassword.value.length < 6) {
    resetPwdError.value = '新密码至少 6 位'
    return
  }
  isSubmittingReset.value = true
  try {
    await api.updateAdminUser(resetTargetUser.value.id, {
      new_password: resetNewPassword.value
    })
    showResetPwdModal.value = false
    ElMessage.success(`已为 ${resetTargetUser.value.username} 重置密码`)
  } catch (err) {
    ElMessage.error(err.message || '重置密码失败')
  } finally {
    isSubmittingReset.value = false
  }
}

const openDelUser = (user) => {
  deleteTargetUser.value = user
  deleteStrategy.value = 'transfer'
  showDelUserModal.value = true
}

const confirmDeleteUser = async () => {
  if (!deleteTargetUser.value) return
  isSubmittingDel.value = true
  try {
    const targetName = deleteTargetUser.value.username
    await api.deleteAdminUser(deleteTargetUser.value.id, deleteStrategy.value)
    showDelUserModal.value = false
    ElMessage.success(
      `已删除用户 ${targetName}，其数据已${deleteStrategy.value === 'transfer' ? '转移给管理员' : '一并删除'}（已自动备份数据库）`
    )
    deleteTargetUser.value = null
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

defineExpose({ loadUsers })
</script>

<template>
  <section class="admin-page">
    <div class="ap-head">
      <span class="aph-icon">👥</span>
      <div>
        <h1>用户管理</h1>
        <p>管理员专属 · 创建用户、改角色、禁用/启用、重置密码、删除及多用户模式切换</p>
      </div>
      <div class="aph-right">
        <button
          type="button"
          class="mode-toggle-btn"
          :class="{ active: multiUserMode }"
          title="开启后未登录访问接口将返回 401；关闭则单人本地免登录"
          @click="emit('toggle-multi-user', !multiUserMode)"
        >
          <span>🛡️</span>
          <span>{{ multiUserMode ? '多用户鉴权：已开启' : '单人免登录模式' }}</span>
        </button>
        <button type="button" class="btn-primary-sm" @click="openNewUser">
          ＋ 新建用户
        </button>
      </div>
    </div>

    <div class="user-table-wrap">
      <div class="ut-head">
        <span>用户</span>
        <span>角色</span>
        <span>状态</span>
        <span>最后登录</span>
        <span>操作</span>
      </div>

      <div v-if="isLoading && users.length === 0" class="ut-empty">正在加载用户列表...</div>
      <div v-else-if="users.length === 0" class="ut-empty">暂无用户记录</div>

      <div v-for="u in users" :key="u.id" class="ut-row">
        <div class="ut-cell">
          <div class="ut-user">
            <span class="utu-av">{{ (u.display_name || u.username || '?').charAt(0).toUpperCase() }}</span>
            <span>
              <b>{{ u.username }}</b>
              <small>{{ u.display_name }} · {{ u.work_count || 0 }} 部作品 / {{ u.chapter_count || 0 }} 章</small>
            </span>
          </div>
        </div>
        <div class="ut-cell">
          <span class="ut-badge" :class="u.role">
            {{ u.role === 'admin' ? '管理员' : '成员' }}
          </span>
        </div>
        <div class="ut-cell">
          <span class="ut-status" :class="{ off: !u.is_active }">
            <i></i>{{ u.is_active ? '启用' : '禁用' }}
          </span>
        </div>
        <div class="ut-cell">{{ formatTime(u.last_login_at) }}</div>
        <div class="ut-cell">
          <div class="ut-ops">
            <button
              v-if="u.username !== 'admin'"
              type="button"
              class="ut-op"
              @click="handleChangeRole(u)"
            >
              改角色
            </button>
            <button type="button" class="ut-op" @click="openResetPwd(u)">重置密码</button>
            <button
              v-if="u.username !== 'admin'"
              type="button"
              class="ut-op"
              @click="handleToggleActive(u)"
            >
              {{ u.is_active ? '禁用' : '启用' }}
            </button>
            <button
              v-if="u.username !== 'admin' && u.id !== currentUser?.id"
              type="button"
              class="ut-op danger"
              @click="openDelUser(u)"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="user-note">
      ⚠️ 安全与隔离说明：所有密码均通过 PBKDF2-HMAC-SHA256 随机加盐哈希存储；删除用户需二次确认并选择其数据「转移给管理员」或「一并删除」，删除前自动备份 chat_memory.db，避免产生孤儿数据（RK-05）。
    </div>

    <!-- 弹窗 1：新建用户 -->
    <div
      v-if="showNewUserModal"
      class="mini-modal show"
      @click.self="showNewUserModal = false"
    >
      <div class="mm-box">
        <div class="mm-head">＋ 新建用户</div>
        <div class="mm-body">
          <div class="fr">
            <label>用户名（登录账号）</label>
            <input v-model="newUserForm.username" placeholder="如 writer02" />
            <span v-if="newUserErrors.username" class="err show">{{ newUserErrors.username }}</span>
          </div>
          <div class="fr">
            <label>显示名称</label>
            <input v-model="newUserForm.display_name" placeholder="如 林小满" />
          </div>
          <div class="fr">
            <label>角色</label>
            <select v-model="newUserForm.role">
              <option value="member">成员 member（仅个人数据）</option>
              <option value="admin">管理员 admin（全站汇总 + 用户管理）</option>
            </select>
          </div>
          <div class="fr">
            <label>初始密码</label>
            <input v-model="newUserForm.password" type="password" placeholder="至少 6 位" />
            <span v-if="newUserErrors.password" class="err show">{{ newUserErrors.password }}</span>
          </div>
          <div class="mm-hint">密码将使用 PBKDF2-HMAC-SHA256 随机加盐后存储，禁止明文（对应风险 RK-02）。</div>
        </div>
        <div class="mm-foot">
          <button type="button" class="btn-ghost" @click="showNewUserModal = false">取消</button>
          <button
            type="button"
            class="btn-primary-sm"
            :disabled="isSubmittingNew"
            @click="submitNewUser"
          >
            {{ isSubmittingNew ? '创建中...' : '创建用户' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 2：重置密码 -->
    <div
      v-if="showResetPwdModal"
      class="mini-modal show"
      @click.self="showResetPwdModal = false"
    >
      <div class="mm-box">
        <div class="mm-head">🔑 重置用户密码</div>
        <div class="mm-body">
          <div class="mm-desc">
            正在为用户 <b style="color: var(--text-primary)">{{ resetTargetUser?.username }}</b>（{{ resetTargetUser?.display_name }}）设置新密码。
          </div>
          <div class="fr">
            <label>新密码</label>
            <input
              v-model="resetNewPassword"
              type="password"
              placeholder="请输入至少 6 位新密码"
              @keyup.enter="submitResetPwd"
            />
            <span v-if="resetPwdError" class="err show">{{ resetPwdError }}</span>
          </div>
        </div>
        <div class="mm-foot">
          <button type="button" class="btn-ghost" @click="showResetPwdModal = false">取消</button>
          <button
            type="button"
            class="btn-primary-sm"
            :disabled="isSubmittingReset"
            @click="submitResetPwd"
          >
            {{ isSubmittingReset ? '提交中...' : '确认重置' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 弹窗 3：删除用户二次确认 -->
    <div
      v-if="showDelUserModal"
      class="mini-modal show"
      @click.self="showDelUserModal = false"
    >
      <div class="mm-box">
        <div class="mm-head">⚠️ 删除用户</div>
        <div class="mm-body">
          <div class="mm-desc">
            即将删除用户 <b style="color: var(--text-primary)">{{ deleteTargetUser?.username }}</b>（{{ deleteTargetUser?.display_name }}）。
            该用户当前共有 <b>{{ deleteTargetUser?.work_count || 0 }}</b> 部作品、<b>{{ deleteTargetUser?.chapter_count || 0 }}</b> 章正文。
          </div>
          <div class="fr">
            <label>该用户的作品 / 数据如何处理？</label>
            <select v-model="deleteStrategy">
              <option value="transfer">转移给当前管理员（推荐，保留数据）</option>
              <option value="delete">一并删除其全部业务数据</option>
            </select>
          </div>
          <div class="mm-warn">此操作不可撤销，删除前系统会自动备份 chat_memory.db。</div>
        </div>
        <div class="mm-foot">
          <button type="button" class="btn-ghost" @click="showDelUserModal = false">取消</button>
          <button
            type="button"
            class="btn-ghost btn-danger-outline"
            :disabled="isSubmittingDel"
            @click="confirmDeleteUser"
          >
            {{ isSubmittingDel ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.admin-page {
  padding: 24px 28px 40px;
  max-width: 1280px;
  margin: 0 auto;
}

.ap-head {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 20px;
  flex-wrap: wrap;
}

.ap-head .aph-icon {
  width: 38px;
  height: 38px;
  border-radius: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--accent-gradient);
  font-size: 19px;
  flex: none;
}

.ap-head h1 {
  font-size: 19px;
  font-weight: 700;
  color: var(--text-primary);
  line-height: 1.25;
  margin: 0;
}

.ap-head p {
  font-size: 12px;
  color: var(--text-muted);
  margin: 4px 0 0;
}

.ap-head .aph-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mode-toggle-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 13px;
  border-radius: 9px;
  border: 1px solid var(--border-color);
  background: var(--bg-secondary);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}

.mode-toggle-btn:hover {
  border-color: rgba(59, 130, 246, 0.45);
  color: var(--text-primary);
}

.mode-toggle-btn.active {
  color: #10b981;
  background: rgba(16, 185, 129, 0.12);
  border-color: rgba(16, 185, 129, 0.4);
}

.btn-primary-sm {
  background: var(--accent-gradient);
  color: #ffffff;
  font-size: 12.5px;
  font-weight: 600;
  padding: 9px 15px;
  border-radius: 9px;
  border: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.25);
}

.btn-primary-sm:hover:not(:disabled) {
  filter: brightness(1.08);
}

.btn-primary-sm:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.user-table-wrap {
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  overflow: hidden;
}

.ut-head,
.ut-row {
  display: grid;
  grid-template-columns: 1.5fr 0.8fr 0.8fr 1.2fr 1.5fr;
  align-items: center;
  gap: 10px;
  padding: 0 18px;
}

.ut-head {
  height: 42px;
  background: var(--bg-tertiary);
  font-size: 11px;
  color: var(--text-secondary);
  font-weight: 600;
}

.ut-row {
  min-height: 58px;
  border-top: 1px solid var(--border-color);
  font-size: 12.5px;
  color: var(--text-secondary);
}

.ut-row:hover {
  background: rgba(255, 255, 255, 0.02);
}

.ut-empty {
  padding: 36px 18px;
  text-align: center;
  font-size: 12.5px;
  color: var(--text-muted);
}

.ut-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.ut-user {
  display: flex;
  align-items: center;
  gap: 9px;
  min-width: 0;
}

.ut-user .utu-av {
  width: 30px;
  height: 30px;
  border-radius: 9px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #ffffff;
  font-size: 12px;
  font-weight: 700;
  flex: none;
}

.ut-user b {
  font-size: 12.5px;
  color: var(--text-primary);
  font-weight: 600;
}

.ut-user small {
  display: block;
  font-size: 10.5px;
  color: var(--text-muted);
}

.ut-badge {
  font-size: 10.5px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 99px;
}

.ut-badge.admin {
  color: #c4b5fd;
  background: rgba(139, 92, 246, 0.16);
  border: 1px solid rgba(139, 92, 246, 0.3);
}

.ut-badge.member {
  color: #7dd3fc;
  background: rgba(14, 165, 233, 0.14);
  border: 1px solid rgba(14, 165, 233, 0.28);
}

.ut-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
}

.ut-status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--success-color, #10b981);
}

.ut-status.off {
  color: var(--text-muted);
}

.ut-status.off i {
  background: var(--text-muted);
}

.ut-ops {
  display: flex;
  gap: 5px;
  flex-wrap: wrap;
}

.ut-op {
  font-size: 11px;
  color: var(--text-secondary);
  padding: 4px 8px;
  border-radius: 6px;
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  cursor: pointer;
  white-space: nowrap;
}

.ut-op:hover {
  color: var(--accent-color);
  border-color: rgba(59, 130, 246, 0.45);
}

.ut-op.danger {
  color: #f87171;
}

.ut-op.danger:hover {
  border-color: rgba(239, 68, 68, 0.5);
}

.user-note {
  margin-top: 14px;
  font-size: 11px;
  color: var(--warning-color, #f59e0b);
  line-height: 1.6;
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.25);
  border-radius: 8px;
  padding: 10px 14px;
}

/* 弹窗样式（还原原型 .mini-modal） */
.mini-modal {
  position: fixed;
  inset: 0;
  z-index: 150;
  background: rgba(2, 6, 23, 0.66);
  backdrop-filter: blur(3px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.mm-box {
  width: 440px;
  max-width: 100%;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: 14px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

.mm-head {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
  font-size: 15px;
  font-weight: 700;
  color: var(--text-primary);
  display: flex;
  align-items: center;
  gap: 9px;
}

.mm-body {
  padding: 18px 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.mm-desc {
  font-size: 12.5px;
  color: var(--text-secondary);
  line-height: 1.6;
}

.mm-hint {
  font-size: 11px;
  color: var(--text-muted);
  line-height: 1.5;
}

.mm-warn {
  font-size: 11px;
  color: var(--warning-color, #f59e0b);
  line-height: 1.5;
}

.mm-body .fr {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mm-body .fr label {
  font-size: 11.5px;
  color: var(--text-secondary);
  font-weight: 600;
}

.mm-body .fr input,
.mm-body .fr select {
  height: 38px;
  background: var(--bg-primary);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--text-primary);
  outline: none;
}

.mm-body .fr input:focus,
.mm-body .fr select:focus {
  border-color: var(--accent-color);
}

.mm-body .fr .err {
  color: #f87171;
  font-size: 11px;
}

.mm-foot {
  padding: 14px 20px;
  border-top: 1px solid var(--border-color);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.btn-ghost {
  padding: 9px 15px;
  border-radius: 9px;
  font-size: 12.5px;
  color: var(--text-secondary);
  border: 1px solid var(--border-color);
  background: var(--bg-tertiary);
  cursor: pointer;
}

.btn-ghost:hover:not(:disabled) {
  color: var(--text-primary);
}

.btn-danger-outline {
  color: #f87171;
  border-color: rgba(239, 68, 68, 0.4);
}

.btn-danger-outline:hover:not(:disabled) {
  background: rgba(239, 68, 68, 0.15);
  color: #fca5a5;
}
</style>

