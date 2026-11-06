// Element Plus 全局样式与暗黑主题变量
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'

// 按需引入用到的组件
import {
  ElButton,
  ElInput,
  ElSelect,
  ElOption,
  ElContainer,
  ElAside,
  ElHeader,
  ElMain,
  ElFooter,
  ElScrollbar,
  ElEmpty,
  ElTag,
  ElAlert,
  ElAvatar,
  ElIcon,
  ElCollapseTransition,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElTooltip,
  ElDialog,
  ElMessage,
  ElMessageBox
} from 'element-plus'

// 按需引入用到的图标
import {
  Plus,
  ChatDotRound,
  Delete,
  Fold,
  Expand,
  VideoPause,
  Position,
  RefreshRight,
  Warning,
  CircleCheckFilled,
  CircleCloseFilled,
  ArrowRight,
  ArrowDown,
  CloseBold,
  Check,
  UserFilled,
  Download,
  Upload,
  Document,
  FolderOpened,
  Files,
  MagicStick
} from '@element-plus/icons-vue'

const components = [
  ElButton,
  ElInput,
  ElSelect,
  ElOption,
  ElContainer,
  ElAside,
  ElHeader,
  ElMain,
  ElFooter,
  ElScrollbar,
  ElEmpty,
  ElTag,
  ElAlert,
  ElAvatar,
  ElIcon,
  ElCollapseTransition,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElTooltip,
  ElDialog
]

const icons = {
  Plus,
  ChatDotRound,
  Delete,
  Fold,
  Expand,
  VideoPause,
  Position,
  RefreshRight,
  Warning,
  CircleCheckFilled,
  CircleCloseFilled,
  ArrowRight,
  ArrowDown,
  CloseBold,
  Check,
  UserFilled,
  Download,
  Upload,
  Document,
  FolderOpened,
  Files,
  MagicStick
}

/**
 * 模块化插件安装方法
 * 在 main.js 中执行 app.use(setupElementPlus) 即可
 */
export function setupElementPlus(app) {
  // 注册按需组件
  components.forEach(component => {
    app.component(component.name, component)
  })

  // 注册按需图标组件
  for (const [key, icon] of Object.entries(icons)) {
    app.component(key, icon)
  }
}

// 导出交互反馈 API 及图标对象，供业务按需直接解构引用
export {
  ElMessage,
  ElMessageBox,
  ElDropdown,
  ElDropdownMenu,
  ElDropdownItem,
  ElTooltip,
  ElDialog,
  Plus,
  ChatDotRound,
  Delete,
  Fold,
  Expand,
  VideoPause,
  Position,
  RefreshRight,
  Warning,
  CircleCheckFilled,
  CircleCloseFilled,
  ArrowRight,
  ArrowDown,
  CloseBold,
  Check,
  UserFilled,
  Download,
  Upload,
  Document,
  FolderOpened,
  Files,
  MagicStick
}
