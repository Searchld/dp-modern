# 溜井数字化监控管理平台

云南锡业溜井数字化监控管理平台，基于 Vue3 + Vite + TypeScript 构建的现代化前端项目。

## 技术栈

- **前端框架**: Vue 3.5.13
- **构建工具**: Vite 6.0.5
- **语言**: TypeScript 5.7.2
- **图表库**: ECharts 5.6.0
- **图标库**: Lucide Vue Next

## 功能特性

### 核心模块
- **报警管理** - 实时报警展示、处理、统计
- **设备监控** - 22台设备在线状态探测
- **矿车统计** - 运输中/空闲中数量统计
- **溜井料位** - AI/雷达双数据源料位监测
- **视频监控** - 多路摄像头分组轮播
- **声光喊话** - 远程喊话控制
- **年度出矿** - 柱状图展示年度出矿量
- **出入料日志** - 实时出入料统计与明细

### 技术特性
- WebSocket 实时报警推送
- API 失败自动降级到 Mock 数据
- 设备连通性主动探测
- 多环境变量配置
- TypeScript 类型安全

## 项目结构

```
dp-modern/
├── public/              # 静态资源
│   └── logo.png         # 项目logo
├── src/
│   ├── composables/     # Vue Composables
│   │   └── useDpData.ts # 数据管理逻辑
│   ├── services/        # 服务层
│   │   ├── api.ts       # API 封装
│   │   ├── deviceRegistry.ts # 设备注册表
│   │   ├── mock.ts      # Mock 数据
│   │   └── types.ts     # TypeScript 类型定义
│   ├── styles/          # 样式文件
│   │   └── base.css     # 基础样式
│   ├── App.vue          # 根组件
│   └── main.ts          # 应用入口
├── API文档.md           # 接口文档
├── index.html           # HTML 入口
├── vite.config.ts       # Vite 配置
├── tsconfig.json        # TypeScript 配置
└── package.json         # 项目依赖
```

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发运行

```bash
npm run dev
```

默认访问地址: `http://localhost:8021`

### 构建生产版本

```bash
npm run build
```

### 预览生产构建

```bash
npm run preview
```

## 接口列表

页面读取数据接口：

- `GET /api/dp/warning` - 报警统计汇总
- `GET /api/dp/warning/list?type=全部` - 报警列表
- `GET /api/dp/facility` - 设备状态（前端探测）
- `GET /api/dp/cars` - 矿车统计
- `GET /api/dp/bar` - 年度出矿量
- `GET /api/dp/logs` - 出入料汇总
- `GET /api/dp/select` - 溜井选项
- `GET /api/dp/aiLogs?type=ai&dept=` - 溜井料位
- `GET /api/dp/live` - 视频源列表
- `GET /api/carsLogs` - 出入料明细（分页）
- `WS /webSocket/dpwarn` - 报警实时推送

详细接口文档请查看 [API文档.md](./API文档.md)

## 开发配置

### 代理配置

开发环境默认代理到 `http://127.0.0.1:8002`，可通过环境变量配置：

- `VITE_API_TARGET` - API 代理目标地址
- `VITE_WS_TARGET` - WebSocket 代理目标地址
- `VITE_HANDLE_API_BASE_URL` - 报警处理 API 地址（默认：http://192.168.246.136）

### Mock 数据

当后端接口不可用时，设置 `VITE_USE_MOCK_ON_ERROR=true` 会自动使用演示数据，方便开发调试。

## 数据刷新策略

| 刷新项 | 间隔 |
|--------|------|
| 全量数据刷新 | 180秒 |
| 报警状态轮询 | 45秒 |
| 通知重复提醒 | 45秒 |
| 天气数据更新 | 30分钟 |
| 视频分组轮播 | 60秒 |

## License

LICENSE
