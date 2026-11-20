<script setup>
import { computed } from 'vue'
import {
  ElOption,
  ElPagination,
  ElSelect,
  ElTable,
  ElTableColumn,
  ElTag,
  ElTooltip
} from '../../plugins/element'

const props = defineProps({
  callLogs: {
    type: Object,
    default: () => ({ total: 0, page: 1, size: 10, total_pages: 1, items: [] })
  },
  availableModels: {
    type: Array,
    default: () => []
  },
  statusFilter: {
    type: String,
    default: 'all'
  },
  modelFilter: {
    type: String,
    default: 'all'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['update:statusFilter', 'update:modelFilter', 'filter-change', 'page-change'])

const statusValue = computed({
  get: () => props.statusFilter,
  set: (val) => {
    emit('update:statusFilter', val)
    emit('filter-change')
  }
})

const modelValue = computed({
  get: () => props.modelFilter,
  set: (val) => {
    emit('update:modelFilter', val)
    emit('filter-change')
  }
})

const onCurrentChange = (val) => {
  emit('page-change', val)
}

const getStatusTagType = (status) => {
  if (status === 'success') return 'success'
  if (status === 'error') return 'danger'
  if (status === 'aborted') return 'warning'
  return 'info'
}
</script>

<template>
  <div class="panel mon-call-panel">
    <div class="panel-hd">
      <h3>调用明细</h3>
      <span class="ph-sub">Element Plus 组件化呈现 · 分页与状态/模型筛选</span>
      <span class="ph-right">GET /api/monitor/calls</span>
    </div>

    <!-- 筛选工具条 -->
    <div class="mon-toolbar">
      <span class="mon-tb-label">状态</span>
      <el-select
        v-model="statusValue"
        placeholder="全部状态"
        size="small"
        class="filter-select"
      >
        <el-option label="全部状态" value="all" />
        <el-option label="success" value="success" />
        <el-option label="error" value="error" />
        <el-option label="aborted" value="aborted" />
      </el-select>

      <span class="mon-tb-label" style="margin-left: 8px">模型</span>
      <el-select
        v-model="modelValue"
        placeholder="全部模型"
        size="small"
        class="filter-select"
      >
        <el-option label="全部模型" value="all" />
        <el-option
          v-for="m in availableModels"
          :key="m"
          :label="m"
          :value="m"
        />
      </el-select>

      <span class="mon-tb-count">共 {{ callLogs.total || 0 }} 条</span>
    </div>

    <!-- Element Plus 表格 -->
    <div class="table-container">
      <el-table
        v-loading="loading"
        :data="callLogs.items"
        style="width: 100%"
        size="small"
        class="custom-el-table"
      >
        <el-table-column prop="time_str" label="时间" min-width="155">
          <template #default="{ row }">
            <span class="mon-mono">{{ row.time_str || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="model" label="模型" min-width="135">
          <template #default="{ row }">
            <span class="mon-mono font-medium">{{ row.model }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="total_tokens" label="Token" min-width="95" align="right">
          <template #default="{ row }">
            <span class="mon-num font-semibold">
              {{ row.total_tokens ? row.total_tokens.toLocaleString('en-US') : '0' }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="duration_ms" label="耗时" min-width="85" align="right">
          <template #default="{ row }">
            <span class="mon-num">{{ (row.duration_ms / 1000).toFixed(1) }}s</span>
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" min-width="95" align="center">
          <template #default="{ row }">
            <el-tag
              :type="getStatusTagType(row.status)"
              size="small"
              effect="light"
              round
            >
              {{ row.status }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="error_msg" label="错误原因" min-width="180">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.error_msg"
              :content="row.error_msg"
              placement="top"
              :show-after="200"
            >
              <span class="mon-err-msg">{{ row.error_msg }}</span>
            </el-tooltip>
            <span v-else class="text-slate-500">—</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- Element Plus 分页器 -->
    <div class="pager-wrapper">
      <el-pagination
        v-model:current-page="callLogs.page"
        :page-size="callLogs.size"
        :total="callLogs.total"
        layout="prev, pager, next, total"
        size="small"
        background
        @current-change="onCurrentChange"
      />
    </div>
  </div>
</template>

<style scoped>
.panel {
  background: var(--bg-secondary, #1e293b);
  border: 1px solid var(--border-color, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  padding: 16px 18px;
}

.panel-hd {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
}

.panel-hd h3 {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--text-primary, #f8fafc);
  margin: 0;
}

.panel-hd .ph-sub {
  font-size: 11px;
  color: var(--text-muted, #64748b);
  margin-left: 2px;
}

.panel-hd .ph-right {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted, #64748b);
}

.mon-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}

.mon-tb-label {
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.filter-select {
  width: 130px;
}

.mon-tb-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--text-muted, #94a3b8);
}

.table-container {
  overflow-x: auto;
  border-radius: 8px;
}

.custom-el-table {
  --el-table-bg-color: transparent;
  --el-table-tr-bg-color: transparent;
  --el-table-header-bg-color: var(--bg-primary, #0f172a);
  --el-table-border-color: var(--border-color, rgba(255, 255, 255, 0.08));
  --el-table-text-color: var(--text-secondary, #cbd5e1);
  --el-table-header-text-color: var(--text-muted, #94a3b8);
  --el-table-row-hover-bg-color: rgba(255, 255, 255, 0.03);
}

.mon-mono {
  font-family: var(--font-mono, monospace);
  font-size: 11.5px;
}

.mon-num {
  font-variant-numeric: tabular-nums;
  color: var(--text-primary, #f8fafc);
}

.mon-err-msg {
  font-family: var(--font-mono, monospace);
  font-size: 11px;
  color: var(--danger-color, #ef4444);
  max-width: 220px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: inline-block;
  cursor: pointer;
}

.pager-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 14px;
  padding-top: 10px;
}
</style>

