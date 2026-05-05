# ynxy-dp-modern

独立于 `ynxy-web` 的 Vue3 + Vite 溜井大屏参考项目，内置方案2「黑金工业指挥」和方案4「全息地图」两套可切换主题。

## 接口

页面按现有 `ynxy-web/src/views/dp/dp-page.vue` 的接口读取数据：

- `GET /api/dp/warning`
- `GET /api/dp/warning/list?type=全部`
- `GET /api/dp/facility`
- `GET /api/dp/cars`
- `GET /api/dp/bar`
- `GET /api/dp/logs`
- `GET /api/dp/select`
- `GET /api/dp/aiLogs?type=ai&dept=`
- `GET /api/dp/live`
- `WS /webSocket/dpwarn`

开发环境默认代理到 `http://127.0.0.1:8002`。没有后端时，`.env.development` 里 `VITE_USE_MOCK_ON_ERROR=true` 会自动使用演示数据，方便先看视觉效果。

## 运行

```bash
npm install
npm run dev
```

默认端口：`8021`。
