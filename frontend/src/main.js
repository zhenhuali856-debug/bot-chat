import { createApp } from 'vue'
import { setupElementPlus } from './plugins/element'
import router from './router'
import './style.css'
import 'highlight.js/styles/github-dark.css'
import App from './App.vue'

const app = createApp(App)
app.use(setupElementPlus)
app.use(router)
app.mount('#app')
