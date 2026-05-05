export interface WarningSummary {
  total: number
  wcl: number
  cl: number
  ljwcl: number
}

export interface WarningItem {
  id?: string
  type: string
  name: string
  instruction?: string
  ip?: string
  remark?: string
  section?: string
  status?: number | string
  video?: string
  warningTime?: string
  warning_time: string
  handle?: string
  handleTime?: string
  state: number | string
  roter?: string
  router?: string
  route?: string
  img?: string
  imgUrl?: string
  img_url?: string
  image?: string
  imageUrl?: string
  image_url?: string
  pic?: string
  pic_url?: string
  picture?: string
  picture_url?: string
  warning_img?: string
  warningImg?: string
  snapshot?: string
}

export interface DeviceStatus {
  name: string
  total: number
  online: number
  offline: number
}

export interface MineCarStats {
  online: number
  total: number
  offline: number
}

export interface BarPayload {
  total: number
  xA: string[]
  yA: number[]
}

export interface LogsTotal {
  rTotal: number
  rCars: number
  cTotal: number
  cCars: number
}

export interface WellLog {
  name: string
  rTotal: number
  cTotal: number
}

export interface LogsPayload {
  total: LogsTotal
  detail: WellLog[]
}

export interface SelectOption {
  lable: string
  value: string
}

export interface MaterialLevel {
  lname: string
  ton: number
  shitype: string
  status: string | number
  all_quantity: number
  now_quantity: number
}

export interface CameraItem {
  label: string
  url: string
}

export interface CameraCategory {
  label: string
  children: CameraItem[]
}

export interface CarsLogItem {
  id: number | string
  fulls?: string | number
  persons?: string
  lname?: string
  company?: string
  createTime?: string
  car?: string
  cars?: string
  shitype?: string | number
  imgpath?: string
  videopath?: string
  rate?: string | number
  timecha?: string | number
  yiwu?: string
  bigs?: string
  name?: string
}

export interface CarsLogsPayload {
  content: CarsLogItem[]
  totalElements: number
}

export interface CarsLogsParams {
  page: number
  size: number
  sort?: string
  fulls?: string
  lname?: string
  car?: string
  createTime?: string
}
