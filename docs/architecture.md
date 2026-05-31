# Architecture

## Overview

Industrial AI Vision Platform is designed as a modular industrial AI system for smart mining, real-time video analytics, equipment monitoring, and operational visualization.

The platform connects video streams, AI inference, industrial event processing, backend APIs, and dashboard visualization into a unified workflow.

## System Architecture

text RTSP Cameras      │      ▼ GStreamer Video Pipeline      │      ▼ YOLOv8 Object Detection      │      ▼ ByteTrack Multi-Object Tracking      │      ▼ Industrial Event Engine      │      ▼ Backend REST API      │      ▼ Database / Message Queue      │      ▼ Dashboard Visualization 

## Core Modules

### 1. Vision Module

The vision module handles real-time video stream processing and AI inference.

Main responsibilities:

- RTSP stream ingestion
- GStreamer-based decoding
- OpenCV frame processing
- YOLOv8 object detection
- ByteTrack object tracking
- RTMP stream publishing
- Event result generation

Typical use cases:

- Vehicle detection
- Personnel detection
- Safety equipment detection
- Ore unloading detection
- Industrial object recognition

### 2. Industrial Event Engine

The event engine converts detection and tracking results into meaningful industrial events.

Examples:

- Vehicle enters work area
- Vehicle starts unloading
- Vehicle leaves work area
- Person enters restricted area
- Safety violation detected
- Equipment abnormal state detected

The event engine can use state machines, ROI rules, object tracking history, and confidence thresholds to reduce false alarms.

### 3. Backend Service

The backend service provides API access, data persistence, and business integration.

Main responsibilities:

- Receive AI event data
- Store alarm records
- Store production statistics
- Provide dashboard APIs
- Integrate OPC UA / PLC data
- Manage devices and cameras
- Manage users, roles, and permissions

### 4. Dashboard Frontend

The frontend provides real-time visualization for industrial operations.

Main capabilities:

- Real-time monitoring
- Video preview
- Alarm statistics
- Production analytics
- Vehicle trip records
- Historical trend analysis
- Smart mining dashboard

## Data Flow

text Camera Stream   → Video Pipeline   → AI Detection   → Object Tracking   → Event Recognition   → API Upload   → Database   → Dashboard 

## Vision Processing Flow

text Frame Capture   → Preprocessing   → YOLOv8 Inference   → Detection Filtering   → ByteTrack Association   → ROI / Direction / State Analysis   → Event Output   → Annotated Stream Output 

## Industrial Event Example

For smart mining unloading detection:

text Vehicle Detected   → Vehicle Confirmed   → Enter Unloading Area   → Dumping Action Detected   → Empty / Leaving State Confirmed   → Trip Record Generated   → Dashboard Updated 

## Deployment Modes

### Single Node Deployment

All modules run on one industrial computer or edge server.

Suitable for:

- Small sites
- Single-camera scenarios
- Development and testing

### Edge AI Deployment

Vision inference runs on edge devices with GPU acceleration, while backend and dashboard run on a central server.

Suitable for:

- Multi-camera systems
- Real-time inference
- Industrial production environments

### Distributed Deployment

Multiple edge inference nodes send events to a centralized backend platform.

Suitable for:

- Large mining sites
- Multiple production areas
- Centralized monitoring centers

## Recommended Repository Structure

text industrial-ai-vision-platform ├── frontend │   └── dashboard application ├── backend │   └── REST API and business services ├── vision │   ├── detector │   ├── tracker │   ├── stream │   ├── models │   └── configs ├── docs │   ├── architecture.md │   └── deployment.md ├── examples └── README.md 

## Design Goals

- Modular architecture
- Real-time video processing
- Industrial deployment readiness
- Extensible AI model support
- Clear separation between vision, backend, and dashboard
- Support for smart mining and industrial automation scenarios