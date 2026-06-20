// 本地开发默认直连本机后端；容器部署时由 Nginx/入口脚本覆盖。
// 若后端启用了访问鉴权（API_AUTH_TOKEN），在此设置同值的 API_TOKEN 即可。
window.__ENV = window.__ENV || {
  BACKEND_URL: 'http://localhost:8000',
  // API_TOKEN: '',
}
