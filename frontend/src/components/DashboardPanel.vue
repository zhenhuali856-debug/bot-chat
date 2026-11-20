<script setup>
// 向后兼容包装层：已重构迁移至 views/admin/DashboardView.vue
import DashboardView from '../views/admin/DashboardView.vue'
</script>

<template>
  <DashboardView v-bind="$attrs" />
</template>
