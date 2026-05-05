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
  { lable: '总览', value: '总览' },
  { lable: '高峰山4号', value: '4' },
  { lable: '高峰山5号', value: '5' },
  { lable: '53号溜井', value: '53' },
  { lable: '54号溜井', value: '54' },
  { lable: '61号溜井', value: '61' }
]

export const mockMaterials: MaterialLevel[] = [
  { lname: '高峰山4号', ton: 150.95, shitype: '矿石', status: '0', all_quantity: 22, now_quantity: 8.66 },
  { lname: '高峰山5号', ton: 143.65, shitype: '矿石', status: '0', all_quantity: 22, now_quantity: 8.81 },
  { lname: '53号溜井', ton: 663.11, shitype: '矿石', status: '0', all_quantity: 23, now_quantity: 23 },
  { lname: '54号溜井', ton: 503.64, shitype: '废石', status: '1', all_quantity: 23, now_quantity: 23 },
  { lname: '61号溜井', ton: 0, shitype: '矿石', status: '0', all_quantity: 180, now_quantity: 0 },
  { lname: '备用料仓', ton: 120.3, shitype: '矿石', status: '0', all_quantity: 100, now_quantity: 12 }
]

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
