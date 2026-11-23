import axios from 'axios'

// 开发环境走 Vite 代理（/api -> 127.0.0.1:8010），生产可用 VITE_API_BASE 覆盖
const http = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  timeout: 15000
})

http.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const detail = error?.response?.data?.detail
    return Promise.reject(new Error(detail || error.message || '请求失败'))
  }
)

export const fetchDashboard = () => http.get('/api/dashboard')
export const fetchS4 = () => http.get('/api/s4')
export const fetchHealth = () => http.get('/api/health')
