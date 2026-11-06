import { ref } from 'vue'

export const THEME_PRESETS = [
  {
    id: 'dark-default',
    name: '深邃暗黑',
    mode: 'dark',
    primary: '#0f172a',
    secondary: '#1e293b',
    tertiary: '#334155',
    textPrimary: '#f8fafc',
    textSecondary: '#94a3b8',
    textMuted: '#64748b',
    borderColor: 'rgba(255, 255, 255, 0.08)',
    codeBg: '#1e2433',
    reasoningBg: 'rgba(30, 41, 59, 0.6)',
    reasoningBorder: 'rgba(139, 92, 246, 0.3)',
    accent: '#3b82f6',
    previewColor: '#0f172a',
    previewAccent: '#3b82f6'
  },
  {
    id: 'light-clean',
    name: '清新素白',
    mode: 'light',
    primary: '#f8fafc',
    secondary: '#ffffff',
    tertiary: '#e2e8f0',
    textPrimary: '#0f172a',
    textSecondary: '#475569',
    textMuted: '#94a3b8',
    borderColor: 'rgba(0, 0, 0, 0.08)',
    codeBg: '#f1f5f9',
    reasoningBg: 'rgba(241, 245, 249, 0.85)',
    reasoningBorder: 'rgba(59, 130, 246, 0.3)',
    accent: '#2563eb',
    previewColor: '#ffffff',
    previewAccent: '#2563eb'
  },
  {
    id: 'dark-ocean',
    name: '星际深蓝',
    mode: 'dark',
    primary: '#0b1329',
    secondary: '#132042',
    tertiary: '#1d3060',
    textPrimary: '#f0f6fc',
    textSecondary: '#8da2c0',
    textMuted: '#587193',
    borderColor: 'rgba(255, 255, 255, 0.09)',
    codeBg: '#0e1830',
    reasoningBg: 'rgba(19, 32, 66, 0.7)',
    reasoningBorder: 'rgba(56, 189, 248, 0.35)',
    accent: '#0ea5e9',
    previewColor: '#0b1329',
    previewAccent: '#0ea5e9'
  },
  {
    id: 'dark-emerald',
    name: '极光墨绿',
    mode: 'dark',
    primary: '#051b15',
    secondary: '#0b2921',
    tertiary: '#133e33',
    textPrimary: '#f0fdf4',
    textSecondary: '#86efac',
    textMuted: '#4ade80',
    borderColor: 'rgba(255, 255, 255, 0.08)',
    codeBg: '#08231c',
    reasoningBg: 'rgba(11, 41, 33, 0.7)',
    reasoningBorder: 'rgba(52, 211, 153, 0.35)',
    accent: '#10b981',
    previewColor: '#051b15',
    previewAccent: '#10b981'
  },
  {
    id: 'dark-purple',
    name: '赛博霓紫',
    mode: 'dark',
    primary: '#120d24',
    secondary: '#1e163b',
    tertiary: '#2e2259',
    textPrimary: '#faf5ff',
    textSecondary: '#c084fc',
    textMuted: '#a855f7',
    borderColor: 'rgba(255, 255, 255, 0.09)',
    codeBg: '#181230',
    reasoningBg: 'rgba(30, 22, 59, 0.7)',
    reasoningBorder: 'rgba(168, 85, 247, 0.35)',
    accent: '#8b5cf6',
    previewColor: '#120d24',
    previewAccent: '#8b5cf6'
  },
  {
    id: 'warm-sunset',
    name: '日落暖橙',
    mode: 'dark',
    primary: '#1a130e',
    secondary: '#281c15',
    tertiary: '#3d2b20',
    textPrimary: '#fff7ed',
    textSecondary: '#fdba74',
    textMuted: '#fb923c',
    borderColor: 'rgba(255, 255, 255, 0.08)',
    codeBg: '#231812',
    reasoningBg: 'rgba(40, 28, 21, 0.7)',
    reasoningBorder: 'rgba(251, 146, 60, 0.35)',
    accent: '#f97316',
    previewColor: '#1a130e',
    previewAccent: '#f97316'
  }
]

export const ACCENT_PALETTE = [
  '#3b82f6', // 经典蓝
  '#2563eb', // 皇家蓝
  '#0ea5e9', // 天空青
  '#10b981', // 翡翠绿
  '#8b5cf6', // 优雅紫
  '#ec4899', // 浪漫粉
  '#f97316', // 活力橙
  '#eab308'  // 明亮金
]

// 全局单例响应式状态
const currentPresetId = ref('dark-default')
const customAccent = ref('')
const isDarkMode = ref(true)

export function useTheme() {
  const applyTheme = (presetId, customColor = null) => {
    const preset = THEME_PRESETS.find(p => p.id === presetId) || THEME_PRESETS[0]
    currentPresetId.value = preset.id
    isDarkMode.value = preset.mode === 'dark'
    if (customColor) {
      customAccent.value = customColor
    }

    const activeAccent = customAccent.value || preset.accent
    const root = document.documentElement

    // 动态注入 CSS 自定义变量
    root.style.setProperty('--bg-primary', preset.primary)
    root.style.setProperty('--bg-secondary', preset.secondary)
    root.style.setProperty('--bg-tertiary', preset.tertiary)
    root.style.setProperty('--text-primary', preset.textPrimary)
    root.style.setProperty('--text-secondary', preset.textSecondary)
    root.style.setProperty('--text-muted', preset.textMuted)
    root.style.setProperty('--border-color', preset.borderColor)
    root.style.setProperty('--code-bg', preset.codeBg)
    root.style.setProperty('--reasoning-bg', preset.reasoningBg)
    root.style.setProperty('--reasoning-border', preset.reasoningBorder)

    // 主题色动态设置与智能混合
    root.style.setProperty('--accent-color', activeAccent)
    root.style.setProperty('--accent-hover', `color-mix(in srgb, ${activeAccent} 80%, black)`)
    root.style.setProperty('--border-focus', activeAccent)
    root.style.setProperty(
      '--accent-gradient',
      `linear-gradient(135deg, ${activeAccent} 0%, color-mix(in srgb, ${activeAccent} 65%, #a855f7) 100%)`
    )

    // Element Plus 暗色模式适配
    if (preset.mode === 'dark') {
      root.classList.add('dark')
    } else {
      root.classList.remove('dark')
    }

    // 本地持久化
    try {
      localStorage.setItem('rabbit_theme_preset', preset.id)
      if (customAccent.value) {
        localStorage.setItem('rabbit_custom_accent', customAccent.value)
      } else {
        localStorage.removeItem('rabbit_custom_accent')
      }
    } catch (e) {
      console.warn('Failed to save theme to localStorage:', e)
    }
  }

  // 快速明暗切换
  const toggleDarkMode = () => {
    if (isDarkMode.value) {
      // 切换到浅色模式
      applyTheme('light-clean', customAccent.value)
    } else {
      // 切换到深色模式 (默认暗黑)
      applyTheme('dark-default', customAccent.value)
    }
  }

  // 自由调节主色调
  const setCustomAccent = (hexColor) => {
    if (!hexColor) return
    customAccent.value = hexColor
    applyTheme(currentPresetId.value, hexColor)
  }

  // 重置主题颜色
  const resetTheme = () => {
    customAccent.value = ''
    applyTheme('dark-default')
  }

  // 初始化主题加载
  const initTheme = () => {
    try {
      const savedPreset = localStorage.getItem('rabbit_theme_preset') || 'dark-default'
      const savedAccent = localStorage.getItem('rabbit_custom_accent') || ''
      applyTheme(savedPreset, savedAccent || null)
    } catch {
      applyTheme('dark-default')
    }
  }

  return {
    currentPresetId,
    customAccent,
    isDarkMode,
    themePresets: THEME_PRESETS,
    accentPalette: ACCENT_PALETTE,
    applyTheme,
    toggleDarkMode,
    setCustomAccent,
    resetTheme,
    initTheme
  }
}

