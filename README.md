# Industrial AI Vision Platform

An open-source industrial AI platform for smart mining, real-time video analytics, equipment monitoring, and operational visualization.

This project combines:

- Real-time RTSP video streaming
- YOLOv8 object detection
- ByteTrack multi-object tracking
- GStreamer accelerated video pipeline
- Industrial event detection
- Smart mining workflow automation
- OPC UA / PLC integration
- Real-time dashboard visualization
- Production and safety monitoring

## Architecture

RTSP Cameras
↓
GStreamer Pipeline
↓
YOLOv8 Inference
↓
ByteTrack Tracking
↓
Business Event Engine
↓
REST API
↓
Dashboard Visualization

## Features

### Video Analytics

- RTSP video ingestion
- RTMP video publishing
- Hardware accelerated decoding
- CUDA accelerated inference
- Multi-stream processing

### AI Detection

- Vehicle detection
- Personnel detection
- Safety equipment monitoring
- Industrial object recognition
- Custom YOLO model deployment

### Industrial Tracking

- Vehicle tracking
- Loading and unloading detection
- Event correlation
- State machine driven workflows
- Long-term object association

### Smart Mining

- Ore unloading monitoring
- Vehicle trip statistics
- Safety supervision
- Production monitoring
- Intelligent operation analysis

### Dashboard

- Real-time monitoring
- ECharts visualization
- Alarm statistics
- Production analytics
- Historical trend analysis

## Technology Stack

Frontend

- Vue3
- TypeScript
- ECharts
- Vite

Backend

- Java
- Spring Boot
- MySQL

AI Vision

- Python
- YOLOv8
- ByteTrack
- OpenCV
- CUDA
- GStreamer

Industrial Protocols

- OPC UA
- PLC Integration

## Project Goals

This project aims to provide a reusable open-source infrastructure for industrial AI applications, including smart mining, industrial automation, safety monitoring, and real-time operational intelligence.

## License

MIT License
