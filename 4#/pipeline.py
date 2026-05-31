import json
import os
import queue
import signal
import threading
import time
from dataclasses import dataclass, field
from itertools import cycle
from typing import Dict, Optional

import cv2
import numpy as np

from utils.logger_util import LoggerUtil

logger = LoggerUtil.get_logger(__name__)

try:
    from rtsp_rtmp import GStreamerFramePusher
except Exception as exc:
    GStreamerFramePusher = None
    PUSH_IMPORT_ERROR = exc
else:
    PUSH_IMPORT_ERROR = None


@dataclass
class PipelineConfig:
    """推理流水线运行配置。

    这部分参数覆盖了：
    1. 流地址来源（本地/配置文件）
    2. TensorRT 模型与插件路径
    3. 各阶段队列大小与并发数
    4. 拉流重连、限帧、监控日志周期
    """

    source_config_path: str = "config/sources.json"
    local_source: str = ""
    use_server_sources: bool = True
    engine_path: str = "build/yolov8s.engine"
    plugin_library: str = "build/libmyplugins.so"
    capture_queue_size: int = 1
    infer_queue_size: int = 16
    process_queue_size: int = 16
    infer_workers: int = 1
    process_workers: int = 1
    reconnect_interval_sec: float = 5.0
    empty_poll_interval_sec: float = 0.01
    source_latency_ms: int = 150
    target_width: int = 1920
    target_height: int = 1080
    max_submit_fps: float = 10.0
    metrics_interval_sec: int = 30
    placeholder_path: str = "123.jpg"
    push_config_path: str = "config/push_streams.json"
    push_enabled: bool = True
    push_fps: float = 10.0
    push_bitrate_kbps: int = 2000
    push_retry_interval_sec: float = 3.0


@dataclass
class FramePacket:
    stream_id: str
    source_url: str
    frame: np.ndarray
    sequence: int
    captured_at: float
    capture_generation: int = 0


@dataclass
class ProcessPacket:
    frame_packet: FramePacket
    detection_result: object
    infer_cost: float
    created_at: float = field(default_factory=time.time)




class PipelineStats:

    """线程安全的运行计数器。

    用于统计采集、调度、推理、处理、丢帧、重连等指标，
    便于线上观察吞吐与稳定性。
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._values = {
            "captured": 0,
            "capture_dropped": 0,
            "scheduled": 0,
            "schedule_dropped": 0,
            "inferred": 0,
            "process_dropped": 0,
            "processed": 0,
            "reconnects": 0,
            "capture_failures": 0,
            "pushed": 0,
            "push_failures": 0,
        }

    def inc(self, key, value=1):
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value

    def snapshot(self):
        with self._lock:
            return dict(self._values)


class FatalPipelineError(RuntimeError):
    pass


class BoundedDropQueue:
    """有界“保最新”队列。

    队列满时丢弃最旧数据，再写入最新数据。
    适合实时视频场景，优先实时性而非完整历史帧。
    """

    def __init__(self, maxsize, stats: PipelineStats, drop_key: str):
        self._queue = queue.Queue(maxsize=maxsize)
        self._stats = stats
        self._drop_key = drop_key

    def put_latest(self, item):
        try:
            self._queue.put_nowait(item)
            return
        except queue.Full:
            pass

        try:
            self._queue.get_nowait()
            self._stats.inc(self._drop_key)
        except queue.Empty:
            pass

        self._queue.put_nowait(item)

    def get(self, timeout):
        return self._queue.get(timeout=timeout)

    def get_nowait(self):
        return self._queue.get_nowait()


class StreamPushManager:
    """把业务处理后的画框帧推到 RTSP/RTMP 服务。"""

    def __init__(self, config: PipelineConfig, stats: PipelineStats):
        self.config = config
        self.stats = stats
        self.enabled = False
        self.outputs = {}
        self.default_uri = ""
        self.template = ""
        self.fps = config.push_fps
        self.bitrate_kbps = config.push_bitrate_kbps
        self.retry_interval = config.push_retry_interval_sec
        self.pushers = {}
        self.push_fail_counts = {}
        self.max_push_failures = 5
        self.stream_generations = {}
        self.lock = threading.Lock()
        self._load_config()

    def _load_config(self):
        if not self.config.push_enabled:
            return
        if GStreamerFramePusher is None:
            logger.warning("推流模块不可用，已跳过推流: %s", PUSH_IMPORT_ERROR)
            return
        if not os.path.exists(self.config.push_config_path):
            logger.info("推流配置不存在，跳过推流: %s", self.config.push_config_path)
            return

        try:
            with open(self.config.push_config_path, "r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            logger.warning("推流配置加载失败，已跳过推流: %s error=%s", self.config.push_config_path, exc)
            return
        if not isinstance(data, dict) or not data.get("enabled", True):
            logger.info("推流未启用: %s", self.config.push_config_path)
            return

        self.fps = float(data.get("fps", self.fps))
        self.bitrate_kbps = int(data.get("bitrate_kbps", self.bitrate_kbps))
        self.retry_interval = float(data.get("retry_interval_sec", self.retry_interval))
        self.default_uri = str(data.get("default", "")).strip()
        self.template = str(data.get("template", "")).strip()
        raw_outputs = data.get("outputs")
        if raw_outputs is None:
            raw_outputs = {
                key: value
                for key, value in data.items()
                if key not in {"enabled", "fps", "bitrate_kbps", "retry_interval_sec", "default", "template"}
            }
        if isinstance(raw_outputs, dict):
            self.outputs = {str(key): str(value).strip() for key, value in raw_outputs.items() if str(value).strip()}

        self.enabled = bool(self.outputs or self.default_uri or self.template)
        if self.enabled:
            logger.info("推流配置已加载 outputs=%s fps=%s bitrate=%s", len(self.outputs), self.fps, self.bitrate_kbps)

    def _uri_for_stream(self, stream_id):
        stream_id = str(stream_id)
        if stream_id in self.outputs:
            return self.outputs[stream_id]
        if self.default_uri:
            return self.default_uri
        if self.template:
            return self.template.format(stream_id=stream_id)
        return ""

    def write(self, stream_id, frame):
        if not self.enabled or frame is None:
            return
        uri = self._uri_for_stream(stream_id)
        if not uri:
            return

        with self.lock:
            pusher = self.pushers.get(uri)
            if pusher is None:
                pusher = GStreamerFramePusher(
                    uri,
                    fps=self.fps,
                    bitrate_kbps=self.bitrate_kbps,
                    retry_interval=self.retry_interval,
                    logger_obj=logger,
                )
                self.pushers[uri] = pusher
                self.push_fail_counts[uri] = 0

            ok = pusher.write(frame)
            if ok:
                self.push_fail_counts[uri] = 0
                self.stats.inc("pushed")
                return

            self.stats.inc("push_failures")
            self.push_fail_counts[uri] = self.push_fail_counts.get(uri, 0) + 1
            if self.push_fail_counts[uri] >= self.max_push_failures:
                logger.warning(
                    "推流连续失败，重建推流器 stream=%s uri=%s failures=%s",
                    stream_id,
                    uri,
                    self.push_fail_counts[uri],
                )
                old_pusher = self.pushers.pop(uri, None)
                self.push_fail_counts.pop(uri, None)
                if old_pusher is not None:
                    old_pusher.release()

    def reset_stream(self, stream_id, generation=None):
        if not self.enabled:
            return
        uri = self._uri_for_stream(stream_id)
        if not uri:
            return

        with self.lock:
            current_generation = self.stream_generations.get(str(stream_id))
            if generation is not None and current_generation == generation:
                return
            self.stream_generations[str(stream_id)] = generation
            pusher = self.pushers.pop(uri, None)
            self.push_fail_counts.pop(uri, None)
            if pusher is not None:
                logger.info(
                    "采集链路已重连，重置推流 stream=%s generation=%s uri=%s",
                    stream_id,
                    generation,
                    uri,
                )
                pusher.release()

    def release(self):
        with self.lock:
            for pusher in self.pushers.values():
                pusher.release()
            self.pushers = {}
            self.push_fail_counts = {}
            self.stream_generations = {}


class StreamCaptureWorker:
    """单路视频采集线程。

    负责：
    1. 打开视频源（RTSP/GStreamer 或普通 OpenCV 源）
    2. 读取帧并按限帧策略下发
    3. 采集失败时重连并返回占位图兜底
    """

    def __init__(self, stream_id, source_url, config: PipelineConfig, stats: PipelineStats, on_fatal_error):
        self.stream_id = stream_id
        self.source_url = source_url
        self.config = config
        self.stats = stats
        self.on_fatal_error = on_fatal_error
        self.output_queue = BoundedDropQueue(config.capture_queue_size, stats, "capture_dropped")
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.run, name=f"capture-{stream_id}", daemon=True)
        self.sequence = 0
        self.capture = None
        self.capture_generation = 0
        self.last_submit_at = 0.0
        self.placeholder = self._load_placeholder()

    def _load_placeholder(self):
        if os.path.exists(self.config.placeholder_path):
            image = cv2.imread(self.config.placeholder_path)
            if image is not None:
                return image
        return np.zeros((self.config.target_height, self.config.target_width, 3), dtype=np.uint8)

    def start(self):
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        if self.capture is not None:
            self.capture.release()

    def join(self, timeout=None):
        self.thread.join(timeout=timeout)

    def _open_capture(self):
        # 优先使用低延迟 GStreamer RTSP 链路，失败后回退到 OpenCV 默认打开方式。
        if self.source_url.lower().startswith("rtsp://"):
            gst = (
                "rtspsrc location={} latency={} ! rtph265depay ! h265parse ! "
                "nvh265dec ! videoconvert ! appsink sync=false drop=true max-buffers=1"
            ).format(self.source_url, self.config.source_latency_ms)
            capture = cv2.VideoCapture(gst, cv2.CAP_GSTREAMER)
            if capture.isOpened():
                return capture

        source = int(self.source_url) if self.source_url.isdigit() else self.source_url
        capture = cv2.VideoCapture(source)
        return capture

    def _read_frame(self):
        if self.capture is None or not self.capture.isOpened():
            self.capture = self._open_capture()
            self.stats.inc("reconnects")
            self.capture_generation += 1
            logger.info(
                "stream=%s reconnect source=%s generation=%s",
                self.stream_id,
                self.source_url,
                self.capture_generation,
            )

        ok, frame = self.capture.read()
        if ok and frame is not None:
            return frame

        self.stats.inc("capture_failures")
        if self.capture is not None:
            self.capture.release()
            self.capture = None
        time.sleep(self.config.reconnect_interval_sec)
        return self.placeholder.copy()

    def run(self):
        min_interval = 1.0 / self.config.max_submit_fps if self.config.max_submit_fps > 0 else 0.0
        try:
            while not self.stop_event.is_set():
                frame = self._read_frame()
                now = time.time()
                if min_interval and now - self.last_submit_at < min_interval:
                    continue

                self.sequence += 1
                self.last_submit_at = now
                packet = FramePacket(
                    stream_id=self.stream_id,
                    source_url=self.source_url,
                    frame=frame,
                    sequence=self.sequence,
                    captured_at=now,
                    capture_generation=self.capture_generation,
                )
                try:
                    self.output_queue.put_latest(packet)
                    self.stats.inc("captured")
                except queue.Full:
                    self.stats.inc("capture_dropped")
        except Exception as exc:
            self.on_fatal_error(FatalPipelineError(f"采集线程异常 stream={self.stream_id}: {exc}"))


class RoundRobinScheduler:
    """轮询调度器。

    多路视频时按轮询策略公平取帧，避免某一路长期独占推理队列。
    """

    def __init__(self, capture_workers, infer_queue: BoundedDropQueue, stats: PipelineStats, stop_event, poll_interval, on_fatal_error):
        self.capture_workers = capture_workers
        self.infer_queue = infer_queue
        self.stats = stats
        self.stop_event = stop_event
        self.poll_interval = poll_interval
        self.on_fatal_error = on_fatal_error
        self.thread = threading.Thread(target=self.run, name="frame-scheduler", daemon=True)

    def start(self):
        self.thread.start()

    def join(self, timeout=None):
        self.thread.join(timeout=timeout)

    def run(self):
        try:
            workers = list(self.capture_workers)
            if not workers:
                raise FatalPipelineError("没有可用的视频流")

            cursor = cycle(workers)
            while not self.stop_event.is_set():
                moved = False
                for _ in range(len(workers)):
                    worker = next(cursor)
                    try:
                        packet = worker.output_queue.get_nowait()
                    except queue.Empty:
                        continue

                    self.infer_queue.put_latest(packet)
                    self.stats.inc("scheduled")
                    moved = True

                if not moved:
                    time.sleep(self.poll_interval)
        except Exception as exc:
            self.on_fatal_error(FatalPipelineError(f"调度线程异常: {exc}"))


class InferenceWorker:
    """推理线程。

    从推理队列取帧，调用 detector.predict 计算检测结果，
    再把结果放入业务处理队列。
    """

    def __init__(self, worker_id, detector, infer_queue, process_queue, stats, stop_event, poll_interval, on_fatal_error):
        self.worker_id = worker_id
        self.detector = detector
        self.infer_queue = infer_queue
        self.process_queue = process_queue
        self.stats = stats
        self.stop_event = stop_event
        self.poll_interval = poll_interval
        self.on_fatal_error = on_fatal_error
        self.thread = threading.Thread(target=self.run, name=f"infer-{worker_id}", daemon=True)

    def start(self):
        self.thread.start()

    def join(self, timeout=None):
        self.thread.join(timeout=timeout)

    def run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    packet = self.infer_queue.get(timeout=self.poll_interval)
                except queue.Empty:
                    continue

                detection_result = self.detector.predict(packet.frame)
                process_packet = ProcessPacket(
                    frame_packet=packet,
                    detection_result=detection_result,
                    infer_cost=detection_result.infer_cost,
                )
                self.process_queue.put_latest(process_packet)
                self.stats.inc("inferred")
        except Exception as exc:
            self.on_fatal_error(FatalPipelineError(f"推理线程异常 worker={self.worker_id}: {exc}"))


class ProcessWorker:
    """业务处理线程。

    消费推理结果并执行 detector.process_business，
    例如车辆流程判定、告警上报、截图等业务动作。
    """

    def __init__(
        self,
        worker_id,
        detector,
        process_queue,
        stats,
        stop_event,
        poll_interval,
        on_fatal_error,
        push_manager=None,
    ):
        self.worker_id = worker_id
        self.detector = detector
        self.process_queue = process_queue
        self.stats = stats
        self.stop_event = stop_event
        self.poll_interval = poll_interval
        self.on_fatal_error = on_fatal_error
        self.push_manager = push_manager
        self.thread = threading.Thread(target=self.run, name=f"process-{worker_id}", daemon=True)

    def start(self):
        self.thread.start()

    def join(self, timeout=None):
        self.thread.join(timeout=timeout)

    def run(self):
        try:
            while not self.stop_event.is_set():
                try:
                    packet = self.process_queue.get(timeout=self.poll_interval)
                except queue.Empty:
                    continue

                output_frame = self.detector.process_business(packet.frame_packet.stream_id, packet.detection_result)
                if self.push_manager is not None:
                    self.push_manager.reset_stream(
                        packet.frame_packet.stream_id,
                        packet.frame_packet.capture_generation,
                    )
                    self.push_manager.write(packet.frame_packet.stream_id, output_frame)
                self.stats.inc("processed")
        except Exception as exc:
            self.on_fatal_error(FatalPipelineError(f"业务线程异常 worker={self.worker_id}: {exc}"))




class MetricsReporter:

    """周期指标上报线程。

    按固定周期打印吞吐、丢帧、重连、队列积压等关键运行指标。
    """

    def __init__(self, stats, infer_queue, process_queue, stop_event, interval_sec, on_fatal_error):
        self.stats = stats
        self.infer_queue = infer_queue
        self.process_queue = process_queue
        self.stop_event = stop_event
        self.interval_sec = interval_sec
        self.on_fatal_error = on_fatal_error
        self.thread = threading.Thread(target=self.run, name="metrics-reporter", daemon=True)

    def start(self):
        self.thread.start()

    def join(self, timeout=None):
        self.thread.join(timeout=timeout)

    def run(self):
        try:
            while not self.stop_event.wait(self.interval_sec):
                snapshot = self.stats.snapshot()
                logger.info(
                    "pipeline stats captured=%s scheduled=%s inferred=%s processed= %s "
                    "capture_drop=%s schedule_drop=%s "
                    "reconnects=%s capture_failures=%s pushed=%s push_failures=%s infer_q=%s process_q=%s",
                    snapshot["captured"],
                    snapshot["scheduled"],
                    snapshot["inferred"],
                    snapshot["processed"],
                    snapshot["capture_dropped"],
                    snapshot["schedule_dropped"],
                    snapshot["reconnects"],
                    snapshot["capture_failures"],
                    snapshot.get("pushed", 0),
                    snapshot.get("push_failures", 0),
                    self.infer_queue._queue.qsize(),
                    self.process_queue._queue.qsize(),
                )
        except Exception as exc:
            self.on_fatal_error(FatalPipelineError(f"指标线程异常: {exc}"))


class PipelineRuntime:
    """流水线生命周期管理器。

    统一管理所有线程的启动/停止/异常传播。
    任何核心线程发生致命异常时，触发全链路有序退出。
    """

    def __init__(self, detector, config: PipelineConfig, sources: Dict[str, str]):
        self.detector = detector
        self.config = config
        self.sources = sources
        self.stats = PipelineStats()
        self.stop_event = threading.Event()
        self._fatal_error = None
        self._fatal_lock = threading.Lock()
        self.capture_workers = [
            StreamCaptureWorker(stream_id, source_url, config, self.stats, self._set_fatal_error)
            for stream_id, source_url in sources.items()
        ]
        self.infer_queue = BoundedDropQueue(config.infer_queue_size, self.stats, "schedule_dropped")
        self.process_queue = BoundedDropQueue(config.process_queue_size, self.stats, "process_dropped")
        self.push_manager = StreamPushManager(config, self.stats)

        self.scheduler = RoundRobinScheduler(
            self.capture_workers,
            self.infer_queue,
            self.stats,
            self.stop_event,
            config.empty_poll_interval_sec,
            self._set_fatal_error,
        )
        self.infer_workers = [
            InferenceWorker(
                i,
                detector,
                self.infer_queue,
                self.process_queue,
                self.stats,
                self.stop_event,
                config.empty_poll_interval_sec,
                self._set_fatal_error,
            )
            for i in range(config.infer_workers)
        ]
        self.process_workers = [
            ProcessWorker(
                i,
                detector,
                self.process_queue,
                self.stats,
                self.stop_event,
                config.empty_poll_interval_sec,
                self._set_fatal_error,
                self.push_manager,
            )
            for i in range(config.process_workers)
        ]
        self.metrics = MetricsReporter(
            self.stats,
            self.infer_queue,
            self.process_queue,
            self.stop_event,
            config.metrics_interval_sec,
            self._set_fatal_error,
        )

    def _set_fatal_error(self, exc):
        # 只记录第一个致命错误，随后触发停止信号，避免多线程重复抛错污染日志。
        with self._fatal_lock:
            if self._fatal_error is None:
                self._fatal_error = exc
                logger.error("pipeline fatal error: %s", exc, exc_info=exc)
        self.stop_event.set()

    def raise_if_failed(self):
        if self._fatal_error is not None:
            raise self._fatal_error

    def start(self):
        logger.info(
            "pipeline start streams=%s",
            len(self.sources),
        )
        self.raise_if_failed()
        for worker in self.capture_workers:
            worker.start()
        self.scheduler.start()
        for worker in self.infer_workers:
            worker.start()
        for worker in self.process_workers:
            worker.start()
        self.metrics.start()

    def wait_forever(self):
        while not self.stop_event.is_set():
            time.sleep(1)
        self.raise_if_failed()

    def stop(self):
        if self.stop_event.is_set():
            for worker in self.capture_workers:
                worker.stop()
        else:
            self.stop_event.set()
            for worker in self.capture_workers:
                worker.stop()
        for worker in self.capture_workers:
            worker.join(timeout=2)
        self.scheduler.join(timeout=2)
        for worker in self.infer_workers:
            worker.join(timeout=2)
        for worker in self.process_workers:
            worker.join(timeout=2)
        self.metrics.join(timeout=2)
        self.push_manager.release()


def install_signal_handlers(runtime: Optional[PipelineRuntime]):
    """注册进程信号处理器。

    把 SIGINT/SIGTERM 转换为优雅停机，确保线程和资源被正确回收。
    """

    def _handle(signum, frame):
        del frame
        logger.info("收到退出信号 signum=%s", signum)
        if runtime is not None:
            runtime.stop()

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)


def load_sources(config: PipelineConfig):
    """加载视频源配置。

    - 服务器模式：从 SOURCE_CONFIG 指定的 JSON 文件读取多路流
    - 本地模式：读取 LOCAL_SOURCE，未设置则默认摄像头 0
    并在启动前校验模型、插件、占位图等关键文件路径。
    """
    if not os.path.exists(config.engine_path):
        raise FileNotFoundError(f"engine 文件不存在: {config.engine_path}")
    if not os.path.exists(config.plugin_library):
        raise FileNotFoundError(f"plugin 库不存在: {config.plugin_library}")
    if not os.path.exists(config.placeholder_path):
        logger.warning("placeholder 文件不存在，将使用黑图兜底: %s", config.placeholder_path)

    if config.use_server_sources:
        if not os.path.exists(config.source_config_path):
            raise FileNotFoundError(f"source config 不存在: {config.source_config_path}")
        with open(config.source_config_path, "r", encoding="utf-8") as file:
            sources = json.load(file)
        if not isinstance(sources, dict) or not sources:
            raise ValueError(f"source config 无效: {config.source_config_path}")
        return {str(k): str(v) for k, v in sources.items()}

    if not config.local_source:
        return {"local-0": "0"}
    return {"local-0": config.local_source}
