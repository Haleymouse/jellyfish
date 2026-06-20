/**
 * 通用任务轮询工具（带指数退避）。
 *
 * 背景：原先各处用固定 2 秒、上限若干次的 `sleep` 循环各自轮询任务状态，
 * 既无退避、又重复实现。这里抽象为单一原语：
 * - 指数退避（默认 2s 起，×1.6，封顶 10s），降低长耗时任务的空轮询压力；
 * - 与具体 service 解耦（通过 fetchStatus / getStatus 注入），便于复用与单测；
 * - 支持取消与最长时长上限，达到终态/取消/超时即结束。
 */

/** 任务终态集合。 */
export const TERMINAL_TASK_STATUSES = ['succeeded', 'failed', 'cancelled'] as const

export type TerminalTaskStatus = (typeof TERMINAL_TASK_STATUSES)[number]

/** 判断给定状态是否为终态。 */
export function isTerminalTaskStatus(status: string | null | undefined): boolean {
  return !!status && (TERMINAL_TASK_STATUSES as readonly string[]).includes(status)
}

export interface PollTaskOptions<T> {
  /** 拉取一次任务状态的请求。 */
  fetchStatus: () => Promise<T>
  /** 从响应中提取状态字符串；返回 null 表示本次未取到状态，继续轮询。 */
  getStatus: (res: T) => string | null
  /** 每次成功取到响应后的回调（用于更新 UI 状态）。 */
  onUpdate?: (res: T, status: string | null) => void
  /** 返回 true 时中止轮询（如组件已卸载/用户取消）。 */
  isCancelled?: () => boolean
  /** 首次轮询间隔，默认 2000ms。 */
  initialDelayMs?: number
  /** 退避封顶间隔，默认 10000ms。 */
  maxDelayMs?: number
  /** 退避系数，默认 1.6。 */
  backoffFactor?: number
  /** 最长轮询时长，默认 120000ms（达到即停止）。 */
  maxDurationMs?: number
  /** 可注入的 sleep（测试用）。 */
  sleepFn?: (ms: number) => Promise<void>
  /** 可注入的计时（测试用）。 */
  nowFn?: () => number
}

const defaultSleep = (ms: number): Promise<void> =>
  new Promise((resolve) => {
    setTimeout(resolve, ms)
  })

/**
 * 轮询任务直至到达终态、被取消或超时。
 *
 * 返回值：到达终态时返回最后一次响应；被取消或超时返回 null。
 */
export async function pollTaskUntilDone<T>(options: PollTaskOptions<T>): Promise<T | null> {
  const {
    fetchStatus,
    getStatus,
    onUpdate,
    isCancelled,
    initialDelayMs = 2000,
    maxDelayMs = 10000,
    backoffFactor = 1.6,
    maxDurationMs = 120000,
    sleepFn = defaultSleep,
    nowFn = () => Date.now(),
  } = options

  const startedAt = nowFn()
  let delay = initialDelayMs

  while (true) {
    if (isCancelled?.()) return null
    if (nowFn() - startedAt >= maxDurationMs) return null

    await sleepFn(delay)
    if (isCancelled?.()) return null

    const res = await fetchStatus()
    const status = getStatus(res)
    onUpdate?.(res, status)

    if (isTerminalTaskStatus(status)) {
      return res
    }

    delay = Math.min(Math.round(delay * backoffFactor), maxDelayMs)
  }
}
