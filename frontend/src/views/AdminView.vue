<script setup>
// 向后兼容包装层：已重构迁移至 views/admin/AdminLayout.vue
import AdminLayout from './admin/AdminLayout.vue'
</script>

<template>
  <AdminLayout v-bind="$attrs" />
</template>
