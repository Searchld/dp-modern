# 溜井数字化监控管理平台 - 接口文档

## 基础信息

- **Base URL**: 由环境变量 `VITE_API_BASE_URL` 配置，默认为空字符串
- **认证方式**: Cookie `EL-ADMIN-TOEKN` 中的 token，通过 `Authorization` 请求头传递
- **请求超时**: 8000ms
- **Content-Type**: `application/json`
- **CORS**: `credentials: include`

---

## 一、报警管理接口

### 1.1 获取报警统计汇总

**接口路径**: `GET /api/dp/warning`

**描述**: 获取今日报警统计数据

**请求参数**: 无

**响应类型**: `WarningSummary`

```typescript
interface WarningSummary {
  total: number    // 今日报警总数
  wcl: number      // 未处理数量
  cl: number       // 已处理数量
  ljwcl: number    // 累计未处理数量
}
```

**使用场景**: 
- 页面初始化加载
- WebSocket 推送触发刷新
- 定时轮询（45秒）

---

### 1.2 获取报警列表

**接口路径**: `GET /api/dp/warning/list`

**描述**: 根据报警类型获取报警列表

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 报警类型：'全部' / '未处理' / '已处理' |

**响应类型**: `WarningItem[]`

```typescript
interface WarningItem {
  id?: string              // 报警ID（处理接口必需）
  type: string             // 报警类型（如：溜井入料口堆塞、人员进入危险区域）
  name: string             // 报警位置名称
  warning_time: string     // 报警时间（格式：YYYY-MM-DD HH:mm:ss）
  state: number | string   // 处理状态：0-未处理，1-已处理
  roter?: string           // 路由标识：1/2/3（决定调用哪个处理接口）
  status?: number | string // 备用状态字段
  handle?: string          // 处理结果描述
  handleTime?: string      // 处理时间
  // 图片字段（多种命名兼容）
  imageUrl?: string
  image_url?: string
  img?: string
  imgUrl?: string
  warning_img?: string
  snapshot?: string
  // 其他可选字段
  instruction?: string
  ip?: string
  remark?: string
  section?: string
  video?: string
  warningTime?: string
  router?: string
  route?: string
  pic?: string
  pic_url?: string
  picture?: string
  picture_url?: string
  warningImg?: string
}
```

**使用场景**: 
- 页面初始化加载
- 切换报警类型筛选时

---

### 1.3 报警处理（3个路由）

根据报警项的 `roter` 字段决定调用哪个接口：

#### 路由 1（默认）

**接口路径**: `PUT {VITE_HANDLE_API_BASE_URL}/api/alert`

**请求体**:

```typescript
{
  id: string,        // 报警ID
  state: 1,          // 固定为 1
  handleTime: string, // 处理时间
  handle: string     // 处理内容
}
```

#### 路由 2

**接口路径**: `PUT {VITE_HANDLE_API_BASE_URL}/api/ynUser`

**请求体**:

```typescript
{
  id: string,        // 报警ID
  status: '1',       // 固定为字符串 '1'
  handle: string,    // 处理内容
  handleTime: string // 处理时间
}
```

#### 路由 3

**接口路径**: `PUT {VITE_HANDLE_API_BASE_URL}/api/ynUserXj`

**请求体**: 同路由 2

**环境变量**: `VITE_HANDLE_API_BASE_URL`（默认：`http://192.168.246.136`）

---

## 二、设备管理接口

### 2.1 获取设备状态（前端主动探测）

**说明**: 该接口不使用后端 API，而是通过前端直接探测设备 IP 的连通性

**探测方式**: `GET http://{deviceIp}/`

**超时时间**: 由 `VITE_DEVICE_CHECK_TIMEOUT` 配置（默认：1200ms）

**并发数**: 由 `VITE_DEVICE_CHECK_CONCURRENCY` 配置（默认：6）

**缓存时间**: 由 `VITE_DEVICE_CHECK_CACHE_TTL` 配置（默认：120000ms）

**响应类型**: `DeviceStatus[]`

```typescript
interface DeviceStatus {
  name: string    // 设备类型名称（摄像头/RFID阅读器/声光报警器/硬盘录像机）
  total: number   // 设备总数
  online: number  // 在线数量
  offline: number // 离线数量
}
```

**设备清单**: 详见 `src/services/deviceRegistry.ts` 中的 `networkDevices` 数组，包含 22 台设备的 IP 配置

---

## 三、矿车统计接口

### 3.1 获取矿车统计数据

**接口路径**: `GET /api/dp/cars`

**描述**: 获取矿车运行状态统计

**请求参数**: 无

**响应类型**: `MineCarStats`

```typescript
interface MineCarStats {
  online: number   // 运输中数量
  total: number    // 矿车总数
  offline: number  // 空闲中数量
}
```

---

## 四、年度出矿量接口

### 4.1 获取年度出矿量数据

**接口路径**: `GET /api/dp/bar`

**描述**: 获取年度出矿量柱状图数据

**请求参数**: 无

**响应类型**: `BarPayload`

```typescript
interface BarPayload {
  total: number   // 年度累计总量
  xA: string[]    // 月份数组（如：['05月', '06月', ...]）
  yA: number[]    // 对应月份的出矿量
}
```

---

## 五、出入料日志接口

### 5.1 获取出入料汇总

**接口路径**: `GET /api/dp/logs`

**描述**: 获取今日出入料统计数据

**请求参数**: 无

**响应类型**: `LogsPayload`

```typescript
interface LogsPayload {
  total: LogsTotal          // 出入料总计
  detail: WellLog[]         // 各溜井出入料明细
}

interface LogsTotal {
  rTotal: number   // 入料总吨数
  rCars: number    // 入料车次数
  cTotal: number   // 出料总吨数
  cCars: number    // 出料车次数
}

interface WellLog {
  name: string     // 溜井名称
  rTotal: number   // 该溜井入料吨数
  cTotal: number   // 该溜井出料吨数
}
```

---

### 5.2 获取出入料分页明细

**接口路径**: `GET /api/carsLogs`

**描述**: 获取出入料分页记录（用于明细弹窗表格）

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | number | 是 | 页码（从 0 开始） |
| size | number | 是 | 每页条数 |
| sort | string | 否 | 排序字段 |
| fulls | string | 否 | 吨数筛选 |
| lname | string | 否 | 溜井名称筛选 |
| car | string | 否 | 车辆编号筛选 |
| createTime | string | 否 | 时间筛选 |

**响应类型**: `CarsLogsPayload`

```typescript
interface CarsLogsPayload {
  content: CarsLogItem[]    // 数据列表
  totalElements: number     // 总记录数
}

interface CarsLogItem {
  id: number | string       // 记录ID
  lname?: string            // 溜井名称
  company?: string          // 所属中段
  shitype?: string | number // 物料类型（1-矿石，2-废石）
  persons?: string          // 矿种名称
  car?: string              // 运输车辆编号
  cars?: string             // 运输车辆编号（备用）
  bigs?: string             // 大块
  yiwu?: string             // 异物
  fulls?: string | number   // 实际入料重量（吨）
  videopath?: string        // 过程视频路径
  imgpath?: string          // 装载图片路径
  rate?: string | number    // 装载率（%）
  timecha?: string | number // 运图时间（秒）
  createTime?: string       // 卸矿时间
  name?: string             // 车次
}
```

**媒体资源访问**: 
- 视频/图片路径需拼接 `VITE_MEDIA_BASE_URL` 环境变量
- 支持绝对路径（http/https 开头）和相对路径

---

## 六、溜井料位监测接口

### 6.1 获取溜井选项列表

**接口路径**: `GET /api/dp/select`

**描述**: 获取溜井部门/区域筛选选项

**请求参数**: 无

**响应类型**: `SelectOption[]`

```typescript
interface SelectOption {
  lable: string     // 显示名称（如：一坑、二坑、三坑）
  value: string     // 部门ID
  dept_sort?: number // 排序序号
}
```

---

### 6.2 获取溜井料位数据

**接口路径**: `GET /api/dp/aiLogs`

**描述**: 获取溜井料位监测数据（支持 AI 和雷达两种数据源）

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| type | string | 是 | 数据源类型：'ai'-AI统计，'ld'-雷达统计 |
| dept | string | 是 | 部门ID（空字符串表示总览） |

**响应类型**: `MaterialLevel[]`

```typescript
interface MaterialLevel {
  lname: string         // 溜井名称
  ton: number           // 矿石吨数
  shitype: string       // 物料类型
  shitypename?: string  // 物料类型名称
  status: string | number // 设备状态：0-正常，非0-异常
  all_quantity: number  // 容量上限（米）
  now_quantity: number  // 当前料位（米）
  dept?: string         // 所属部门ID
}
```

---

## 七、视频监控接口

### 7.1 获取视频源列表

**接口路径**: `GET /api/dp/live`

**描述**: 获取摄像头分组及视频流地址

**请求参数**: 无

**响应类型**: `CameraCategory[]`

```typescript
interface CameraCategory {
  label: string         // 分组名称（如：一坑、二坑、三坑）
  children: CameraItem[] // 摄像头列表
}

interface CameraItem {
  label: string  // 摄像头名称
  url: string    // 视频流地址（iframe 嵌入）
}
```

---

## 八、声光喊话接口

### 8.1 发送喊话指令

**接口路径**: `GET /api/ynSiren/send/message`

**描述**: 向声光报警器发送喊话内容

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| ip | string | 是 | 设备 IP 地址 |
| text | string | 是 | 喊话内容（最长 120 字符） |
| num | number | 是 | 播放次数（1-10） |

**设备 IP 映射规则**:

| 摄像头关键词 | 设备 IP |
|-------------|---------|
| 1920, 挂车 | 192.168.18.124 |
| 61号, 61# | 192.168.18.118 |
| 54号, 54# | 192.168.18.117 |
| 53号, 53# | 192.168.18.116 |
| 4号, 4# | 192.168.18.115 |
| 5号, 5# | 192.168.18.114 |

---

## 九、WebSocket 实时推送

### 9.1 报警实时推送

**连接地址**: `{VITE_WS_BASE_URL}/webSocket/dpwwarn`

**说明**: 
- 默认使用当前页面协议的 WebSocket（ws:// 或 wss://）
- 可通过 `VITE_WS_BASE_URL` 环境变量配置

**推送消息格式**:

```json
{
  "msg": "报警消息内容"
}
```

或任意 JSON 结构

**触发行为**:
1. 收到消息后刷新报警状态（调用 `/api/dp/warning` 和 `/api/dp/warning/list`）
2. 更新 `wsTick` 计数器触发 UI 更新
3. 如有新报警，显示弹窗通知

---

## 十、数据刷新机制

### 定时刷新策略

| 刷新项 | 间隔 | 环境变量 | 默认值 |
|--------|------|---------|--------|
| 全量数据刷新 | 180秒 | `VITE_FULL_REFRESH_INTERVAL` | 180000ms |
| 报警状态轮询 | 45秒 | `VITE_ALERT_POLL_INTERVAL` | 45000ms |
| 通知重复提醒 | 45秒 | `VITE_NOTICE_REPEAT_INTERVAL` | 45000ms |
| 天气数据更新 | 30分钟 | - | 1800000ms |
| 视频分组轮播 | 60秒 | `VITE_VIDEO_GROUP_CYCLE_INTERVAL` | 60000ms |

### 全量刷新包含接口

调用 `refreshAll()` 时并行请求：
1. `/api/dp/warning` - 报警统计
2. `/api/dp/facility` - 设备状态（通过 IP 探测）
3. `/api/dp/cars` - 矿车统计
4. `/api/dp/bar` - 年度出矿量
5. `/api/dp/logs` - 出入料汇总
6. `/api/dp/select` - 溜井选项
7. `/api/dp/live` - 视频源列表
8. `/api/dp/warning/list` - 报警列表
9. `/api/dp/aiLogs` - 溜井料位

---

## 十一、环境变量清单

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `VITE_API_BASE_URL` | API 基础路径 | 空字符串 |
| `VITE_API_TARGET` | 开发代理目标地址 | `http://127.0.0.1:8002` |
| `VITE_WS_TARGET` | 开发 WebSocket 代理目标 | 同 API_TARGET |
| `VITE_WS_BASE_URL` | WebSocket 基础地址 | 当前页面协议 + host |
| `VITE_HANDLE_API_BASE_URL` | 报警处理 API 地址 | `http://192.168.246.136` |
| `VITE_MEDIA_BASE_URL` | 媒体资源基础 URL | 同 API_TARGET |
| `VITE_USE_MOCK_ON_ERROR` | API 失败时使用 Mock | `true` |
| `VITE_DEVICE_CHECK_TIMEOUT` | 设备探测超时（ms） | 1200 |
| `VITE_DEVICE_CHECK_CACHE_TTL` | 设备状态缓存（ms） | 120000 |
| `VITE_DEVICE_CHECK_CONCURRENCY` | 设备探测并发数 | 6 |
| `VITE_FULL_REFRESH_INTERVAL` | 全量刷新间隔（ms） | 180000 |
| `VITE_ALERT_POLL_INTERVAL` | 报警轮询间隔（ms） | 45000 |
| `VITE_NOTICE_REPEAT_INTERVAL` | 通知重复间隔（ms） | 45000 |
| `VITE_ALARM_SCROLL_SPEED` | 报警列表滚动速度 | 18 |
| `VITE_VIDEO_GROUP_CYCLE_INTERVAL` | 视频轮播间隔（ms） | 60000 |
| `VITE_BAR_VISIBLE_MONTHS` | 柱状图可见月份数 | 6 |
| `VITE_IO_PAGE_SIZE` | 出入料每页条数 | 8 |

---

## 十二、数据下钻关系

```
报警统计
  ├─ 点击"今日报警总数" → 显示报警列表筛选
  └─ 点击"未处理/已处理" → 显示对应报警列表

报警列表
  └─ 点击单条报警 → 显示报警详情（含图片）
      └─ 点击"定位摄像头" → 切换到对应摄像头画面

设备运行状态
  └─ 点击设备类型 → 显示设备详情（总数/在线/离线/在线率）

矿车统计
  ├─ 点击"运输中" → 显示运输中数量详情
  ├─ 点击"总数" → 显示矿车总数详情
  └─ 点击"空闲中" → 显示空闲中数量详情

实时视频监控
  ├─ 点击视频画面 → 切换选中
  ├─ 双击视频画面 → 放大播放
  └─ 点击"喊话" → 发送声光喊话指令

溜井料位监测
  ├─ 切换 AI统计/雷达统计
  ├─ 切换部门筛选
  └─ 点击溜井卡片 → 显示料位详情
      └─ 点击"筛选该溜井" → 切换到对应部门并定位摄像头

年度出矿量
  └─ 点击柱状图 → 显示该月出矿量详情

今日出入料
  ├─ 点击"入料/出料总计" → 显示分页明细表
  ├─ 点击溜井明细 → 显示该溜井出入料详情
  └─ 明细表中点击"查看" → 播放视频或查看图片
```
