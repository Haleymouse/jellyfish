/**
 * 运行时/构建期环境读取工具。
 *
 * 说明：
 * - 运行时配置来自 `/env.js` 注入的 `window.__ENV`（Docker/Nginx 部署使用）；
 * - 构建期配置来自 Vite 的 `import.meta.env.VITE_*`；
 * - 运行时优先于构建期，便于同一镜像在不同环境复用。
 */

declare global {
  interface Window {
    __ENV?: {
      BACKEND_URL?: string
      // 与后端 API_AUTH_TOKEN 对应的访问令牌；后端未启用鉴权时留空即可。
      API_TOKEN?: string
    }
  }
}

/** 读取后端地址（运行时优先，其次构建期）。 */
export function getRuntimeBackendUrl(): string | undefined {
  return window.__ENV?.BACKEND_URL ?? import.meta.env.VITE_BACKEND_URL
}

/**
 * 读取访问令牌（运行时优先，其次构建期）。
 * 返回去除空白后的非空字符串；未配置时返回 undefined，调用方据此决定是否附加鉴权头。
 */
export function getRuntimeApiToken(): string | undefined {
  const token = window.__ENV?.API_TOKEN ?? import.meta.env.VITE_API_TOKEN
  const trimmed = (token ?? '').trim()
  return trimmed ? trimmed : undefined
}

export {}
