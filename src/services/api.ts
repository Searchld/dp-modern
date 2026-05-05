import type {
  BarPayload,
  CameraCategory,
  CarsLogsParams,
  CarsLogsPayload,
  DeviceStatus,
  LogsPayload,
  MaterialLevel,
  MineCarStats,
  SelectOption,
  WarningItem,
  WarningSummary
} from './types'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const REQUEST_TIMEOUT = 8000
const TOKEN_KEY = 'EL-ADMIN-TOEKN'

function buildUrl(path: string, params?: Record<string, string | number | undefined>) {
  if (/^https?:\/\//i.test(path)) {
    const url = new URL(path)
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined) url.searchParams.set(key, String(value))
    })
    return url.toString()
  }

  const normalizedBase = API_BASE.replace(/\/$/, '')
  const normalizedPath = path.startsWith('/') ? path : `/${path}`
  const url = new URL(`${normalizedBase}${normalizedPath}`, window.location.origin)

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value !== undefined) url.searchParams.set(key, String(value))
  })

  return url.toString()
}

export async function request<T>(path: string, params?: Record<string, string | number | undefined>): Promise<T> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
  const token = getCookie(TOKEN_KEY)
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  }

  if (token) {
    headers.Authorization = token
  }

  try {
    const response = await fetch(buildUrl(path, params), {
      method: 'GET',
      headers,
      credentials: 'include',
      signal: controller.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const text = await response.text()
    if (!text) return null as T

    try {
      return JSON.parse(text) as T
    } catch {
      return text as T
    }
  } finally {
    window.clearTimeout(timer)
  }
}

export async function sendJson<T>(path: string, body: unknown, method = 'POST'): Promise<T | null> {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT)
  const token = getCookie(TOKEN_KEY)
  const headers: HeadersInit = {
    'Content-Type': 'application/json'
  }

  if (token) {
    headers.Authorization = token
  }

  try {
    const response = await fetch(buildUrl(path), {
      method,
      headers,
      credentials: 'include',
      body: JSON.stringify(body),
      signal: controller.signal
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`)
    }

    const text = await response.text()
    if (!text) return null

    try {
      return JSON.parse(text) as T
    } catch {
      return text as T
    }
  } finally {
    window.clearTimeout(timer)
  }
}

export function postJson<T>(path: string, body: unknown): Promise<T | null> {
  return sendJson<T>(path, body, 'POST')
}

export function putJson<T>(path: string, body: unknown): Promise<T | null> {
  return sendJson<T>(path, body, 'PUT')
}

function getCookie(name: string) {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1')}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : ''
}

export const dpApi = {
  warningSummary: () => request<WarningSummary>('/api/dp/warning'),
  warningList: (type: string) => request<WarningItem[]>('/api/dp/warning/list', { type }),
  facility: () => request<DeviceStatus[]>('/api/dp/facility'),
  cars: () => request<MineCarStats>('/api/dp/cars'),
  bar: () => request<BarPayload>('/api/dp/bar'),
  logs: () => request<LogsPayload>('/api/dp/logs'),
  select: () => request<SelectOption[]>('/api/dp/select'),
  aiLogs: (type: string, dept: string) => request<MaterialLevel[]>('/api/dp/aiLogs', { type, dept }),
  live: () => request<CameraCategory[]>('/api/dp/live'),
  carsLogs: (params: CarsLogsParams) => request<CarsLogsPayload>('/api/carsLogs', { ...params }),
  sirenMessage: (params: { ip: string; text: string; num: number }) => request<unknown>('/api/ynSiren/send/message', params)
}
