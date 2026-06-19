import { OpenAPI } from './generated'
import { getRuntimeApiToken, getRuntimeBackendUrl } from './runtimeEnv'

/**
 * 初始化由 OpenAPI 生成的请求客户端。
 *
 * 说明：
 * - 生成接口的路径已包含 `/api/v1/...`，因此 BASE 默认应为空串（同源）或完整后端地址。
 * - 本地开发默认直连 `http://localhost:8000`。
 * - 若配置了访问令牌（后端 API_AUTH_TOKEN），通过 OpenAPI.TOKEN 注入，
 *   生成的客户端会自动附加 `Authorization: Bearer <token>`。
 */
export function initOpenAPI(base: string = '') {
  OpenAPI.BASE = base
  const token = getRuntimeApiToken()
  OpenAPI.TOKEN = token
}

const defaultBackendUrl = 'http://localhost:8000'

initOpenAPI(getRuntimeBackendUrl() ?? defaultBackendUrl)
