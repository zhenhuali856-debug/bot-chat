// Element Plus 组件样式按需引入
import 'element-plus/es/components/button/style/css'
import 'element-plus/es/components/input/style/css'
import 'element-plus/es/components/select/style/css'
import 'element-plus/es/components/option/style/css'
import 'element-plus/es/components/container/style/css'
import 'element-plus/es/components/aside/style/css'
import 'element-plus/es/components/header/style/css'
import 'element-plus/es/components/main/style/css'
import 'element-plus/es/components/footer/style/css'
import 'element-plus/es/components/scrollbar/style/css'
import 'element-plus/es/components/empty/style/css'
import 'element-plus/es/components/tag/style/css'
import 'element-plus/es/components/alert/style/css'
import 'element-plus/es/components/avatar/style/css'
import 'element-plus/es/components/message/style/css'
import 'element-plus/es/components/message-box/style/css'
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
  ArrowDown
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
  ElCollapseTransition
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
  ArrowDown
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
  ArrowDown
}

