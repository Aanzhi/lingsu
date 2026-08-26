import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import './lingsu-system.css'
import App from './App.vue'
import { router } from './router'
const app = createApp(App)
  .use(ElementPlus)
  .use(router)
app.mount('#app')
