# 视频分析系统

## 项目概述

本项目是一个基于 TensorRT 的视频分析系统，用于对视频流进行实时分析，包括车辆检测、人员安全检测、溜井状态检测等功能。

## 目录结构

```
├── build/              # 模型和插件目录
│   ├── yolov8s.engine  # TensorRT 模型引擎
│   └── libmyplugins.so # TensorRT 插件库
├── config/             # 配置文件目录
│   └── sources.json    # 视频源配置
├── utils/              # 工具类目录
│   └── logger_util.py  # 日志工具
├── 123.jpg             # 无视频流时的兜底图片
├── dect.py             # 业务逻辑处理
├── infer.py            # 启动入口
├── pipeline.py         # 视频处理管道
├── start.sh            # 启动脚本
├── stop.sh             # 停止脚本
└── yoLov8TRT.py        # TensorRT 推理实现
```

## 配置文件说明

### `config/sources.json`

视频源配置文件，定义相机标识到 RTSP 流地址的映射。channel 编号会自动从流地址中提取（例如 `stream_2` 中的 `2`）：

```json
{
  "192.168.18.119": "rtsp://192.168.18.119:10086/stream_2"
}
```

## 启动和停止

### 启动服务

```bash
./start.sh
```

### 停止服务

```bash
./stop.sh
```

## 依赖项

- Python 3.8+
- OpenCV
- NumPy
- TensorRT
- PyCUDA
- Shapely
- Requests

## 部署说明

1. **环境准备**
   - 安装 Python 3.8+
   - 安装必要的依赖包
   - 确保 CUDA 环境正确配置

2. **配置修改**
   - 修改 `config/sources.json` 中的视频源地址
   - 根据实际部署环境修改 `start.sh` 中的 `APP_HOME` 和 `PYTHON_BIN`

3. **模型文件**
   - 将 `yolov8s.engine` 和 `libmyplugins.so` 放置在 `build/` 目录下

4. **权限设置**
   - 确保 `start.sh` 和 `stop.sh` 有执行权限：
     ```bash
     chmod +x start.sh stop.sh
     ```
   - 确保 `logs/` 目录有写入权限

## 日志说明

- **日志文件**：`logs/app.log`
- **日志分割**：每 2MB 自动分割，最多保留 10 个备份文件
- **日志格式**：包含时间戳、级别、进程ID、线程名、模块名、行号、消息

## 常见问题

1. **视频流无法连接**
   - 检查网络连接
   - 确认 RTSP 地址正确
   - 检查相机是否在线

2. **模型加载失败**
   - 确认 `build/` 目录下有正确的模型文件
   - 检查 CUDA 环境配置

3. **日志文件过大**
   - 日志会自动按 2MB 分割，无需手动清理

4. **服务启动失败**
   - 查看 `logs/infer.log` 和 `logs/app.log` 了解具体错误信息

## 技术栈

- **推理引擎**：TensorRT
- **视频处理**：OpenCV
- **业务逻辑**：Python
- **部署方式**：后台服务

## 功能特点

- **实时视频分析**：基于 TensorRT 实现高效推理
- **多目标检测**：支持车辆、人员、安全装备等多种目标检测
- **业务规则处理**：根据检测结果执行相应的业务逻辑
- **自动重连**：视频流中断后自动尝试重连
- **详细日志**：完整的日志记录，便于问题排查
