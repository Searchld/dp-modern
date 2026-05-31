# Industrial AI Vision Platform

Open-source Industrial AI Platform for Smart Mining, Real-Time Video Analytics, Computer Vision, and Operational Monitoring.

## Overview

Industrial AI Vision Platform is a practical framework designed for industrial environments, combining computer vision, video streaming, industrial automation, and operational dashboards.

The platform supports real-time monitoring, AI inference, event detection, production analytics, and safety supervision for mining and industrial scenarios.

## Key Features

### AI Vision

- YOLOv8 Object Detection
- ByteTrack Multi-Object Tracking
- Vehicle Tracking
- Personnel Detection
- Safety Monitoring
- Custom Model Deployment

### Video Streaming

- RTSP Input
- RTMP Output
- GStreamer Pipeline
- Hardware Accelerated Decoding
- CUDA Inference
- Multi-Stream Processing

### Industrial Automation

- OPC UA Integration
- PLC Connectivity
- Event-Driven Workflows
- State Machine Processing
- Alarm Management

### Smart Mining

- Ore Unloading Detection
- Vehicle Trip Statistics
- Production Monitoring
- Safety Supervision
- Intelligent Event Analysis

### Dashboard

- Real-Time Visualization
- ECharts Analytics
- Alarm Statistics
- Production Reports
- Historical Trends

## Architecture

text RTSP Camera       │       ▼ GStreamer Pipeline       │       ▼ YOLOv8 Inference       │       ▼ ByteTrack Tracking       │       ▼ Business Event Engine       │       ▼ REST API       │       ▼ Dashboard 

## Project Structure

text industrial-ai-platform ├── frontend ├── backend ├── vision ├── docs ├── examples └── README.md 

## Technology Stack

### Frontend

- Vue3
- TypeScript
- Vite
- ECharts

### Backend

- Java
- Spring Boot
- MySQL

### AI Vision

- Python
- YOLOv8
- ByteTrack
- OpenCV
- CUDA
- GStreamer

### Industrial Protocols

- OPC UA
- PLC Integration

## Use Cases

- Smart Mining
- Industrial Automation
- Safety Monitoring
- Vehicle Tracking
- Production Analytics
- Real-Time Video Intelligence

## Roadmap

- [ ] Multi-Camera Management
- [ ] Distributed Inference
- [ ] Model Management
- [ ] Edge Deployment
- [ ] Industrial Knowledge Base
- [ ] AI Assistant Integration

## License

MIT License
