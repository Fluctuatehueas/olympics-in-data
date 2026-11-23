import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    // 5500 落在 Windows 的保留端口段（5474–5573），改到 8080
    port: 8090,
    // 可选：如果端口被占用，直接退出，而不是自动切换到下一个端口
    strictPort: true,
    proxy:{
      '/api': {
        //填写真实的后端地址
        target: 'http://127.0.0.1:8010',
        changeOrigin: true
      }
    }
  }
})
