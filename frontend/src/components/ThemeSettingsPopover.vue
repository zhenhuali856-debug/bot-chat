<script setup>
import { computed } from 'vue'
import {
  Sunny,
  Moon,
  Check,
  RefreshRight,
  ElColorPicker,
  ElPopover
} from '../plugins/element'
import { useTheme } from '../composables/useTheme'

const {
  currentPresetId,
  customAccent,
  isDarkMode,
  themePresets,
  accentPalette,
  applyTheme,
  toggleDarkMode,
  setCustomAccent,
  resetTheme
} = useTheme()

const currentActiveAccent = computed(() => {
  if (customAccent.value) return customAccent.value
  const p = themePresets.find(item => item.id === currentPresetId.value)
  return p ? p.accent : '#3b82f6'
})

const handleSelectPreset = (presetId) => {
  applyTheme(presetId, customAccent.value)
}

const handleColorPickerChange = (color) => {
  if (color) {
    setCustomAccent(color)
  }
}
</script>

<template>
  <div class="theme-settings-wrapper flex items-center gap-1.5">
    <!-- 1. 快速一键明暗切换按钮 -->
    <el-tooltip :content="isDarkMode ? '切换到明亮模式' : '切换到暗黑模式'" placement="bottom">
      <el-button
        circle
        text
        class="theme-mode-btn"
        :icon="isDarkMode ? Sunny : Moon"
        @click="toggleDarkMode"
      />
    </el-tooltip>

    <!-- 2. 主题与配色自由调节 Popover -->
    <el-popover
      placement="bottom-end"
      :width="300"
      trigger="click"
      popper-class="theme-settings-popover"
    >
      <template #reference>
        <el-button
          plain
          size="small"
          class="theme-palette-btn"
          title="自由调节页面颜色与主题"
        >
          <span
            class="accent-preview-dot mr-1.5"
            :style="{ backgroundColor: currentActiveAccent }"
          ></span>
          <span>配色</span>
        </el-button>
      </template>

      <div class="theme-popover-content">
        <!-- 弹窗标题 -->
        <div class="popover-header">
          <div class="header-title">🎨 页面主题与颜色调节</div>
          <button class="reset-link-btn" title="恢复默认深邃暗黑" @click="resetTheme">
            <el-icon><RefreshRight /></el-icon>
            <span>重置</span>
          </button>
        </div>

        <!-- 预设主题风格选择 -->
        <div class="section-label">预设风格方案</div>
        <div class="preset-grid">
          <div
            v-for="p in themePresets"
            :key="p.id"
            class="preset-card"
            :class="{ active: currentPresetId === p.id }"
            @click="handleSelectPreset(p.id)"
          >
            <div
              class="preset-color-box"
              :style="{ backgroundColor: p.previewColor, borderColor: p.previewAccent }"
            >
              <div
                class="preset-inner-accent"
                :style="{ backgroundColor: p.previewAccent }"
              ></div>
              <el-icon v-if="currentPresetId === p.id" class="preset-check-icon">
                <Check />
              </el-icon>
            </div>
            <span class="preset-name">{{ p.name }}</span>
          </div>
        </div>

        <!-- 自由调节主色调 (Accent Color) -->
        <div class="section-label mt-3">主色调自由定制</div>
        <div class="accent-palette-row">
          <button
            v-for="c in accentPalette"
            :key="c"
            class="palette-swatch"
            :class="{ active: currentActiveAccent.toLowerCase() === c.toLowerCase() }"
            :style="{ backgroundColor: c }"
            :title="c"
            @click="setCustomAccent(c)"
          >
            <el-icon v-if="currentActiveAccent.toLowerCase() === c.toLowerCase()" class="swatch-check">
              <Check />
            </el-icon>
          </button>

          <!-- 自定义拾色器 -->
          <div class="custom-color-picker-wrap" title="自定义任意 Hex/RGB 颜色">
            <el-color-picker
              v-model="customAccent"
              size="small"
              :show-alpha="false"
              @change="handleColorPickerChange"
            />
          </div>
        </div>

        <div class="theme-footer-hint">
          💡 所选颜色将即时生效并自动持久化到本地。
        </div>
      </div>
    </el-popover>
  </div>
</template>

<style scoped>
.theme-mode-btn {
  font-size: 1.1rem;
  color: var(--text-secondary) !important;
  transition: all 0.2s ease;
}

.theme-mode-btn:hover {
  color: var(--accent-color) !important;
  background: rgba(255, 255, 255, 0.08) !important;
}

.theme-palette-btn {
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04) !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-primary) !important;
  padding: 0 10px;
  height: 28px;
  font-size: 0.82rem;
  transition: all 0.2s ease;
}

.theme-palette-btn:hover {
  border-color: var(--accent-color) !important;
  background: rgba(255, 255, 255, 0.08) !important;
}

.accent-preview-dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  box-shadow: 0 0 6px rgba(0, 0, 0, 0.3);
}

.theme-popover-content {
  padding: 4px;
}

.popover-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-color);
}

.header-title {
  font-size: 0.88rem;
  font-weight: 600;
  color: var(--text-primary);
}

.reset-link-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  background: transparent;
  border: none;
  font-size: 0.74rem;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 2px 6px;
  border-radius: 4px;
  transition: all 0.15s ease;
}

.reset-link-btn:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}

.section-label {
  font-size: 0.74rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 8px;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.preset-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 8px 6px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  background: rgba(255, 255, 255, 0.02);
  transition: all 0.15s ease;
}

.preset-card:hover {
  background: rgba(255, 255, 255, 0.06);
}

.preset-card.active {
  border-color: var(--accent-color);
  background: rgba(59, 130, 246, 0.12);
}

.preset-color-box {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 2px solid;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.preset-inner-accent {
  width: 12px;
  height: 12px;
  border-radius: 50%;
}

.preset-check-icon {
  position: absolute;
  font-size: 0.95rem;
  color: #fff;
  filter: drop-shadow(0 1px 2px rgba(0, 0, 0, 0.8));
}

.preset-name {
  font-size: 0.72rem;
  color: var(--text-secondary);
}

.preset-card.active .preset-name {
  color: var(--text-primary);
  font-weight: 600;
}

/* 主色调选择器 */
.accent-palette-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 7px;
  padding: 4px 0;
}

.palette-swatch {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: 2px solid transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
}

.palette-swatch:hover {
  transform: scale(1.15);
}

.palette-swatch.active {
  border-color: #ffffff;
  transform: scale(1.1);
  box-shadow: 0 0 8px var(--accent-color);
}

.swatch-check {
  font-size: 0.8rem;
  color: #ffffff;
}

.custom-color-picker-wrap :deep(.el-color-picker__trigger) {
  width: 24px !important;
  height: 24px !important;
  padding: 0 !important;
  border-radius: 50% !important;
  overflow: hidden;
  border: 2px dashed rgba(255, 255, 255, 0.3) !important;
}

.theme-footer-hint {
  margin-top: 10px;
  font-size: 0.7rem;
  color: var(--text-muted);
  line-height: 1.4;
  border-top: 1px dashed var(--border-color);
  padding-top: 6px;
}
</style>

