import type {
  BarPayload,
  CameraCategory,
  DeviceStatus,
  LogsPayload,
  MaterialLevel,
  MineCarStats,
  SelectOption,
  WarningItem,
  WarningSummary
} from './types'

export const mockWarningSummary: WarningSummary = {
  total: 33,
  wcl: 33,
  cl: 0,
  ljwcl: 26809
}

export const mockWarnings: WarningItem[] = [
  { type: '溜井入料口堆塞', name: '高峰山5号', warning_time: '2026-04-28 10:33:34', state: 0, roter: '1' },
  { type: '人员进入危险区域', name: '53号溜井', warning_time: '2026-04-28 10:04:51', state: 0, roter: '2' },
  { type: '溜井入料口堆塞', name: '54号溜井', warning_time: '2026-04-28 10:12:07', state: 1, roter: '1' },
  { type: '车辆长时间停留', name: '高峰山4号', warning_time: '2026-04-28 12:22:55', state: 0, roter: '1' },
  { type: '车辆长时间停留', name: '高峰山4号', warning_time: '2026-04-28 12:22:55', state: 0, roter: '1' },
  { type: '车辆长时间停留', name: '高峰山4号', warning_time: '2026-04-28 12:22:55', state: 0, roter: '1' },
  { type: '车辆长时间停留', name: '高峰山4号', warning_time: '2026-04-28 12:22:55', state: 0, roter: '1' },
  { type: '安全帽识别异常', name: '61号溜井', warning_time: '2026-04-28 14:18:06', state: 1, roter: '2' }
]

export const mockDevices: DeviceStatus[] = [
  { name: '摄像头', total: 8, online: 8, offline: 0 },
  { name: 'RFID阅读器', total: 5, online: 4, offline: 1 },
  { name: '声光报警器', total: 6, online: 6, offline: 0 },
  { name: '硬盘录像机', total: 3, online: 3, offline: 0 }
]

export const mockMineCars: MineCarStats = {
  online: 16,
  total: 67,
  offline: 51
}

export const mockBar: BarPayload = {
  total: 266097.07,
  xA: ['05月', '06月', '07月', '08月', '09月', '10月', '11月', '12月', '01月', '02月', '03月', '04月'],
  yA: [0, 0, 0, 0, 0, 0, 0, 49000, 50500, 87000, 79500, 0]
}

export const mockLogs: LogsPayload = {
  total: {
    rTotal: 1976.72,
    rCars: 134,
    cTotal: 2094.02,
    cCars: 18
  },
  detail: [
    { name: '高峰山4号', rTotal: 223.23, cTotal: 100.06 },
    { name: '高峰山5号', rTotal: 213.67, cTotal: 175.86 },
    { name: '53号溜井', rTotal: 1287.47, cTotal: 1272.5 },
    { name: '54号溜井', rTotal: 252.35, cTotal: 105.4 },
    { name: '61号溜井', rTotal: 0, cTotal: 0 }
  ]
}

export const mockSelectOptions: SelectOption[] = [
  { lable: '一坑', value: '5288924761098241', dept_sort: 1 },
  { lable: '三坑', value: '5288924472756225', dept_sort: 3 }
]

export const mockMaterials: MaterialLevel[] = [
  { lname: '34号溜井', ton: 0, shitype: '1660矿', shitypename: '高、低氧矿', status: 0, all_quantity: 180, now_quantity: 0, dept: '5288924761098241' },
  { lname: '61号溜井', ton: 0, shitype: '1660矿', shitypename: '高、低氧矿', status: 0, all_quantity: 180, now_quantity: 0, dept: '5288924761098241' },
  { lname: '高峰山4号', ton: 150.95, shitype: '矿石', shitypename: '矿石', status: 0, all_quantity: 22, now_quantity: 8.66, dept: '5288924472756225' },
  { lname: '高峰山5号', ton: 143.65, shitype: '矿石', shitypename: '矿石', status: 0, all_quantity: 22, now_quantity: 8.81, dept: '5288924472756225' },
  { lname: '53号溜井', ton: 663.11, shitype: '矿石', shitypename: '矿石', status: 0, all_quantity: 23, now_quantity: 23, dept: '5288924472756225' },
  { lname: '54号溜井', ton: 503.64, shitype: '废石', shitypename: '废石', status: 1, all_quantity: 23, now_quantity: 23, dept: '5288924472756225' },
  { lname: '55号溜井', ton: 320.78, shitype: '矿石', shitypename: '矿石', status: 0, all_quantity: 25, now_quantity: 15.3, dept: '5288924472756225' },
  { lname: '56号溜井', ton: 180.45, shitype: '废石', shitypename: '废石', status: 0, all_quantity: 20, now_quantity: 9.2, dept: '5288924472756225' },
  { lname: '57号溜井', ton: 450.23, shitype: '矿石', shitypename: '高品位矿', status: 0, all_quantity: 30, now_quantity: 20.8, dept: '5288924472756225' },
  { lname: '58号溜井', ton: 78.91, shitype: '矿石', shitypename: '低品位矿', status: 0, all_quantity: 18, now_quantity: 4.5, dept: '5288924472756225' },
  { lname: '备用料仓', ton: 120.3, shitype: '矿石', shitypename: '矿石', status: 0, all_quantity: 100, now_quantity: 12, dept: '' }
]

export const mockRadarMaterials: MaterialLevel[] = mockMaterials.map(item => {
  const maxLevel = Number(item.all_quantity || 0)
  const level = Number(item.now_quantity || 0)
  const adjustedLevel = maxLevel ? Math.min(maxLevel, Math.max(0, level + (level >= maxLevel ? 0 : 0.42))) : level

  return {
    ...item,
    ton: Number((Number(item.ton || 0) * 0.98).toFixed(2)),
    now_quantity: Number(adjustedLevel.toFixed(2))
  }
})

export const mockLive: CameraCategory[] = [
  {
    label: '一坑',
    children: [
      { label: '61号溜井入料口', url: 'about:blank' }
    ]
  },
  {
    label: '二坑',
    children: [
      { label: '1920挂车点', url: 'about:blank' },
      { label: '1920挂车点1', url: 'about:blank' },
      { label: '1920斜井巷道', url: 'about:blank' }
    ]
  },
  {
    label: '三坑',
    children: [
      { label: '高峰山4号入料口', url: 'about:blank' },
      { label: '高峰山5号入料口', url: 'about:blank' },
      { label: '53号溜井入料口', url: 'about:blank' },
      { label: '54号溜井入料口', url: 'about:blank' },
      { label: '61号溜井入料口2', url: 'about:blank' }
    ]
  }
]
