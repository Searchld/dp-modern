import type { DeviceStatus } from './types'

type DeviceKind = '摄像头' | 'RFID阅读器' | '声光报警器' | '硬盘录像机'

interface NetworkDevice {
  kind: DeviceKind
  name: string
  area: string
  location: string
  ip: string
}

const DEVICE_TIMEOUT = Number(import.meta.env.VITE_DEVICE_CHECK_TIMEOUT || 1200)
const DEVICE_CACHE_TTL = Number(import.meta.env.VITE_DEVICE_CHECK_CACHE_TTL || 120000)
const DEVICE_CHECK_CONCURRENCY = Number(import.meta.env.VITE_DEVICE_CHECK_CONCURRENCY || 6)

const deviceKinds: DeviceKind[] = ['摄像头', 'RFID阅读器', '声光报警器', '硬盘录像机']
let cachedStatuses: DeviceStatus[] | null = null
let cachedAt = 0

export const networkDevices: NetworkDevice[] = [
  { kind: '声光报警器', name: '声光报警器 (1920挂车点)', area: '1920斜井巷道', location: '1920斜井巷道', ip: '192.168.18.124' },
  { kind: '声光报警器', name: '61#溜井', area: '61#溜井巷道', location: '61#溜井巷道', ip: '192.168.18.118' },
  { kind: '声光报警器', name: '54#溜井', area: '54#溜井巷道', location: '54#溜井巷道', ip: '192.168.18.117' },
  { kind: '声光报警器', name: '53#溜井', area: '53#溜井巷道', location: '53#溜井巷道', ip: '192.168.18.116' },
  { kind: '声光报警器', name: '4#溜井', area: '4#溜井巷道', location: '4#溜井巷道', ip: '192.168.18.115' },
  { kind: '声光报警器', name: '5#溜井', area: '5#溜井巷道', location: '5#溜井巷道', ip: '192.168.18.114' },
  { kind: '摄像头', name: '5#溜井入料口摄像头', area: '三坑', location: '5#溜井口上方', ip: '192.168.18.103' },
  { kind: '摄像头', name: '4#溜井入料口摄像头', area: '三坑', location: '4#溜井口上方', ip: '192.168.18.104' },
  { kind: '摄像头', name: '53#溜井入料口摄像头', area: '三坑', location: '53#溜井口上方', ip: '192.168.18.105' },
  { kind: '摄像头', name: '54#溜井入料口摄像头', area: '三坑', location: '54#溜井口上方', ip: '192.168.18.106' },
  { kind: '摄像头', name: '61#溜井入料口摄像头', area: '一坑', location: '34#溜井口上方（1540）', ip: '192.168.18.107' },
  { kind: '摄像头', name: '1920挂车点', area: '二坑', location: '', ip: '192.168.18.122' },
  { kind: '摄像头', name: '1920挂车点1', area: '二坑', location: '1920斜井巷道', ip: '192.168.18.123' },
  { kind: '硬盘录像机', name: '硬盘录像机（机房）', area: '1360数据机房', location: '数据机房', ip: '192.168.18.100' },
  { kind: '硬盘录像机', name: '硬盘录像机（4#、5#、53#、54#）', area: '4#/5#溜井设备箱', location: '4#/5#溜井设备箱', ip: '192.168.18.101' },
  { kind: '硬盘录像机', name: '硬盘录像机（34#）', area: '34#溜井设备箱', location: '34#溜井设备箱', ip: '192.168.18.102' },
  { kind: 'RFID阅读器', name: '61#溜井', area: '61#溜井巷道', location: '61#溜井巷道', ip: '192.168.18.113' },
  { kind: 'RFID阅读器', name: '54#溜井', area: '54#溜井巷道', location: '54#溜井巷道', ip: '192.168.18.112' },
  { kind: 'RFID阅读器', name: '53#溜井', area: '53#溜井巷道', location: '53#溜井巷道', ip: '192.168.18.111' },
  { kind: 'RFID阅读器', name: '4#溜井', area: '4#溜井巷道', location: '4#溜井巷道', ip: '192.168.18.110' },
  { kind: 'RFID阅读器', name: '5#溜井', area: '5#溜井巷道', location: '5#溜井巷道', ip: '192.168.18.109' }
]

async function probeIp(ip: string) {
  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), DEVICE_TIMEOUT)

  try {
    await fetch(`http://${ip}/`, {
      method: 'GET',
      mode: 'no-cors',
      cache: 'no-store',
      signal: controller.signal
    })
    return true
  } catch {
    return false
  } finally {
    window.clearTimeout(timer)
  }
}

export async function checkDeviceStatuses(): Promise<DeviceStatus[]> {
  const now = Date.now()
  if (cachedStatuses && now - cachedAt < DEVICE_CACHE_TTL) return cachedStatuses

  const uniqueIps = Array.from(new Set(networkDevices.map(item => item.ip)))
  const pairs: Array<readonly [string, boolean]> = []

  for (let index = 0; index < uniqueIps.length; index += DEVICE_CHECK_CONCURRENCY) {
    const group = uniqueIps.slice(index, index + DEVICE_CHECK_CONCURRENCY)
    pairs.push(...await Promise.all(group.map(async ip => [ip, await probeIp(ip)] as const)))
  }

  const reachable = new Map(pairs)

  cachedStatuses = deviceKinds.map(kind => {
    const devices = networkDevices.filter(item => item.kind === kind)
    const online = devices.filter(item => reachable.get(item.ip)).length

    return {
      name: kind,
      total: devices.length,
      online,
      offline: devices.length - online
    }
  })
  cachedAt = now
  return cachedStatuses
}
