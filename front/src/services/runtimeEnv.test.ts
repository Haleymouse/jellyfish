import { afterEach, describe, expect, it } from 'vitest'

import { getRuntimeApiToken, getRuntimeBackendUrl } from './runtimeEnv'

afterEach(() => {
  window.__ENV = undefined
})

describe('getRuntimeBackendUrl', () => {
  it('优先返回运行时 window.__ENV.BACKEND_URL', () => {
    window.__ENV = { BACKEND_URL: 'http://runtime:8000' }
    expect(getRuntimeBackendUrl()).toBe('http://runtime:8000')
  })

  it('未配置时返回 undefined（回退到构建期/默认由调用方处理）', () => {
    window.__ENV = {}
    expect(getRuntimeBackendUrl()).toBeUndefined()
  })
})

describe('getRuntimeApiToken', () => {
  it('返回去空白后的非空令牌', () => {
    window.__ENV = { API_TOKEN: '  secret-token  ' }
    expect(getRuntimeApiToken()).toBe('secret-token')
  })

  it('空串/纯空白视为未配置，返回 undefined', () => {
    window.__ENV = { API_TOKEN: '   ' }
    expect(getRuntimeApiToken()).toBeUndefined()
  })

  it('未设置时返回 undefined', () => {
    window.__ENV = {}
    expect(getRuntimeApiToken()).toBeUndefined()
  })
})
