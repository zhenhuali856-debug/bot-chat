<script setup>
// 向后兼容包装层：已重构迁移至 views/workspace/WorkspaceView.vue
import WorkspaceView from './workspace/WorkspaceView.vue'
</script>

<template>
  <WorkspaceView v-bind="$attrs" />
</template>
