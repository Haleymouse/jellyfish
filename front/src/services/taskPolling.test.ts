import { describe, expect, it, vi } from 'vitest'

import { isTerminalTaskStatus, pollTaskUntilDone } from './taskPolling'

describe('isTerminalTaskStatus', () => {
  it('识别终态', () => {
    expect(isTerminalTaskStatus('succeeded')).toBe(true)
    expect(isTerminalTaskStatus('failed')).toBe(true)
    expect(isTerminalTaskStatus('cancelled')).toBe(true)
  })

  it('非终态与空值返回 false', () => {
    expect(isTerminalTaskStatus('running')).toBe(false)
    expect(isTerminalTaskStatus('pending')).toBe(false)
    expect(isTerminalTaskStatus(null)).toBe(false)
    expect(isTerminalTaskStatus(undefined)).toBe(false)
  })
})

describe('pollTaskUntilDone', () => {
  const noSleep = () => Promise.resolve()

  it('轮询到终态返回最后一次响应', async () => {
    const statuses = ['pending', 'running', 'succeeded']
    let i = 0
    const fetchStatus = vi.fn(async () => ({ status: statuses[i++] }))
    const onUpdate = vi.fn()

    const res = await pollTaskUntilDone({
      fetchStatus,
      getStatus: (r) => r.status,
      onUpdate,
      sleepFn: noSleep,
    })

    expect(res).toEqual({ status: 'succeeded' })
    expect(fetchStatus).toHaveBeenCalledTimes(3)
    expect(onUpdate).toHaveBeenCalledTimes(3)
  })

  it('被取消时返回 null 且不再请求', async () => {
    const fetchStatus = vi.fn(async () => ({ status: 'running' }))
    const res = await pollTaskUntilDone({
      fetchStatus,
      getStatus: (r) => r.status,
      isCancelled: () => true,
      sleepFn: noSleep,
    })
    expect(res).toBeNull()
    expect(fetchStatus).not.toHaveBeenCalled()
  })

  it('超时返回 null', async () => {
    let clock = 0
    const fetchStatus = vi.fn(async () => ({ status: 'running' }))
    const res = await pollTaskUntilDone({
      fetchStatus,
      getStatus: (r) => r.status,
      maxDurationMs: 5000,
      sleepFn: noSleep,
      nowFn: () => {
        clock += 3000
        return clock
      },
    })
    expect(res).toBeNull()
  })

  it('应用指数退避（间隔递增并封顶）', async () => {
    const delays: number[] = []
    const sleepFn = vi.fn(async (ms: number) => {
      delays.push(ms)
    })
    const statuses = ['running', 'running', 'running', 'running', 'succeeded']
    let i = 0
    await pollTaskUntilDone({
      fetchStatus: async () => ({ status: statuses[i++] }),
      getStatus: (r) => r.status,
      initialDelayMs: 2000,
      backoffFactor: 2,
      maxDelayMs: 10000,
      maxDurationMs: 10_000_000,
      sleepFn,
    })
    // 2000 -> 4000 -> 8000 -> 10000(封顶) -> 10000
    expect(delays).toEqual([2000, 4000, 8000, 10000, 10000])
  })

  it('status 为 null 时继续轮询', async () => {
    const statuses: (string | null)[] = [null, null, 'succeeded']
    let i = 0
    const res = await pollTaskUntilDone({
      fetchStatus: async () => ({ status: statuses[i++] }),
      getStatus: (r) => r.status,
      sleepFn: noSleep,
    })
    expect(res).toEqual({ status: 'succeeded' })
  })
})
