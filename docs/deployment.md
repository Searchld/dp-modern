# Deployment Guide

## Overview

This document describes how to deploy Industrial AI Vision Platform for development, testing, and industrial edge scenarios.

The platform may include the following modules:

- Frontend dashboard
- Backend REST API
- Vision inference service
- RTSP / RTMP video pipeline
- Database
- OPC UA / PLC integration

## Recommended Environment

### Operating System

Recommended:

- Ubuntu 20.04+
- Ubuntu 22.04 LTS

### Hardware

For AI inference:

- NVIDIA GPU recommended
- CUDA-compatible driver
- 8GB+ RAM
- SSD storage
- Stable network connection to cameras

For dashboard-only deployment:

- 2 CPU cores+
- 4GB+ RAM

## Software Dependencies

### Frontend

- Node.js
- pnpm / npm
- Vue3
- Vite

### Backend

- Java 17+
- Spring Boot
- MySQL

### Vision Module

- Python 3.8+
- OpenCV
- PyTorch
- Ultralytics YOLOv8
- GStreamer
- CUDA
- ByteTrack

## Project Structure

text industrial-ai-vision-platform ├── frontend ├── backend ├── vision ├── docs ├── examples └── README.md 

## Frontend Deployment

Enter the frontend directory:

bash cd frontend 

Install dependencies:

bash pnpm install 

Start development server:

bash pnpm dev 

Build production files:

bash pnpm build 

The generated static files can be deployed with Nginx.

## Backend Deployment

Enter the backend directory:

bash cd backend 

Build the backend service:

bash mvn clean package 

Run the service:

bash java -jar target/app.jar 

Recommended configuration items:

yaml server:   port: 8080  spring:   datasource:     url: jdbc:mysql://localhost:3306/industrial_ai     username: root     password: your_password 

## Vision Module Deployment

Enter the vision directory:

bash cd vision 

Create Python virtual environment:

bash python3 -m venv venv source venv/bin/activate 

Install dependencies:

bash pip install -r requirements.txt 

Run a single RTSP stream inference task:

bash python rtsp_rtmp.py \   --source rtsp://user:password@camera-ip/stream \   --output rtmp://server/live/stream_1 \   --model models/best.pt 

## GStreamer Pipeline Example

Example RTSP input pipeline:

text rtspsrc location=rtsp://camera-url latency=50   ! rtph264depay   ! h264parse   ! nvh264dec   ! videoconvert   ! appsink 

Example RTMP output pipeline:

text appsrc is-live=true block=true do-timestamp=true   ! videoconvert   ! video/x-raw,format=I420   ! nvh264enc preset=low-latency-hq bitrate=2000   ! h264parse config-interval=1   ! flvmux streamable=true   ! rtmpsink location=rtmp://server/live/stream_1 

## Configuration Example

Create a config file:

yaml camera:   id: stream_1   source: rtsp://user:password@camera-ip/stream   output: rtmp://server/live/stream_1  model:   path: models/best.pt   confidence: 0.5   device: cuda:0  event:   enable_tracking: true   enable_roi: true   upload_api: http://localhost:8080/api/ai/events 

## Nginx Deployment

Example Nginx static frontend configuration:

nginx server {     listen 80;     server_name localhost;      root /var/www/industrial-ai-platform;     index index.html;      location / {         try_files $uri $uri/ /index.html;     }      location /api/ {         proxy_pass http://127.0.0.1:8080/;         proxy_set_header Host $host;         proxy_set_header X-Real-IP $remote_addr;     } } 

## Production Recommendations

- Use environment variables for passwords and tokens
- Do not commit real RTSP URLs
- Do not commit private model files if they are not intended to be public
- Use HTTPS for public deployments
- Use process managers such as systemd, Docker, or supervisor
- Enable log rotation
- Monitor GPU, CPU, memory, and stream status
- Add automatic restart for vision services
- Isolate industrial control networks from public networks

## Security Notes

Avoid exposing the following information:

- Camera passwords
- RTSP URLs
- API tokens
- PLC addresses
- OPC UA credentials
- Internal server IPs
- Private model weights

Use placeholder configuration files for open-source examples.

## Deployment Checklist

- [ ] Frontend build completed
- [ ] Backend service started
- [ ] Database initialized
- [ ] Vision dependencies installed
- [ ] GStreamer available
- [ ] CUDA available
- [ ] Model file configured
- [ ] RTSP source tested
- [ ] RTMP output tested
- [ ] API upload tested
- [ ] Dashboard data displayed correctly