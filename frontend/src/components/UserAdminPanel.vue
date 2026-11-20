<script setup>
// 向后兼容包装层：已重构迁移至 views/admin/UserAdminView.vue
import UserAdminView from '../views/admin/UserAdminView.vue'
</script>

<template>
  <UserAdminView v-bind="$attrs" />
</template>
