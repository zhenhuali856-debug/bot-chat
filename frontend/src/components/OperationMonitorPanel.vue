<script setup>
// 向后兼容包装层：已重构迁移至 views/admin/MonitorView.vue
import MonitorView from '../views/admin/MonitorView.vue'
</script>

<template>
  <MonitorView v-bind="$attrs" />
</template>
